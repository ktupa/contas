"""
Serviço de gerenciamento de certificados digitais A1
"""
from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
import io
import hashlib
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile, HTTPException

from app.models import CompanyCertificate, Company
from app.crypto_service import CryptoService
from app.storage import MinIOService as StorageService

logger = logging.getLogger(__name__)


class CertificateService:
    """Serviço para gerenciar certificados digitais A1 (.pfx)"""
    
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageService,
        crypto: CryptoService
    ):
        self.db = db
        self.storage = storage
        self.crypto = crypto
    
    async def validate_and_extract_cert_info(
        self,
        pfx_data: bytes,
        password: str
    ) -> Tuple[datetime, datetime, str]:
        """
        Valida o certificado e extrai informações
        
        Args:
            pfx_data: Bytes do arquivo .pfx
            password: Senha do certificado
            
        Returns:
            (valid_from, valid_to, thumbprint)
            
        Raises:
            ValueError: Se o certificado for inválido
        """
        try:
            # Carrega o certificado .pfx
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data,
                password.encode('utf-8'),
                backend=default_backend()
            )
            
            if not certificate:
                raise ValueError("Certificado não encontrado no arquivo .pfx")

            # Extrai informações (compatível com cryptography < 42.0)
            valid_from = certificate.not_valid_before
            valid_to = certificate.not_valid_after
            
            # Converte para timezone-aware UTC para validação
            if valid_from.tzinfo is None:
                valid_from = valid_from.replace(tzinfo=timezone.utc)
            else:
                valid_from = valid_from.astimezone(timezone.utc)
            if valid_to.tzinfo is None:
                valid_to = valid_to.replace(tzinfo=timezone.utc)
            else:
                valid_to = valid_to.astimezone(timezone.utc)
            
            # Gera thumbprint (SHA-256 do certificado)
            thumbprint = hashlib.sha256(certificate.public_bytes(Encoding.DER)).hexdigest()
            
            # Verifica se ainda está válido
            now = datetime.now(timezone.utc)
            if now > valid_to:
                raise ValueError(f"Certificado expirado em {valid_to}")
            
            if now < valid_from:
                raise ValueError(f"Certificado ainda não é válido (válido a partir de {valid_from})")
            
            # Persiste como datetimes ingênuos em UTC (coluna sem timezone)
            valid_from = valid_from.replace(tzinfo=None)
            valid_to = valid_to.replace(tzinfo=None)
            
            logger.info(f"Certificado validado: thumbprint={thumbprint[:16]}..., válido até {valid_to}")
            
            return valid_from, valid_to, thumbprint
            
        except Exception as e:
            logger.error(f"Erro ao validar certificado: {e}")
            raise ValueError(f"Certificado inválido: {str(e)}")
    
    async def upload_certificate(
        self,
        company_id: int,
        pfx_file: UploadFile,
        password: str
    ) -> CompanyCertificate:
        """
        Faz upload e valida um certificado para uma empresa
        
        Args:
            company_id: ID da empresa
            pfx_file: Arquivo .pfx
            password: Senha do certificado
            
        Returns:
            CompanyCertificate criado/atualizado
        """
        try:
            # Verifica se a empresa existe
            company_result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = company_result.scalar_one_or_none()
            if not company:
                raise HTTPException(status_code=404, detail="Empresa não encontrada")
            
            # Lê os bytes do arquivo
            pfx_data = await pfx_file.read()
            
            # Valida o certificado e extrai informações
            valid_from, valid_to, thumbprint = await self.validate_and_extract_cert_info(
                pfx_data, password
            )
            
            # Salva o .pfx no storage
            cnpj = company.cnpj or "sem_cnpj"
            storage_key = f"certs/{company_id}/{cnpj}/cert.pfx"
            self.storage.put_object(
                storage_key,
                pfx_data,
                "application/x-pkcs12"
            )
            
            # Criptografa a senha
            password_enc = self.crypto.encrypt(password)
            
            # Verifica se já existe certificado para esta empresa
            cert_result = await self.db.execute(
                select(CompanyCertificate).where(
                    CompanyCertificate.company_id == company_id
                )
            )
            existing_cert = cert_result.scalar_one_or_none()
            
            if existing_cert:
                # Atualiza certificado existente
                existing_cert.cnpj = cnpj
                existing_cert.cert_storage_key = storage_key
                existing_cert.cert_password_enc = password_enc
                existing_cert.cert_thumbprint = thumbprint
                existing_cert.valid_from = valid_from
                existing_cert.valid_to = valid_to
                existing_cert.status = "active"
                existing_cert.last_error = None
                existing_cert.updated_at = datetime.utcnow()
                certificate = existing_cert
            else:
                # Cria novo certificado
                certificate = CompanyCertificate(
                    company_id=company_id,
                    cnpj=cnpj,
                    cert_storage_key=storage_key,
                    cert_password_enc=password_enc,
                    cert_thumbprint=thumbprint,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    status="active",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(certificate)
            
            await self.db.commit()
            await self.db.refresh(certificate)
            
            logger.info(f"Certificado salvo para empresa {company_id}, válido até {valid_to}")
            return certificate
            
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Erro ao fazer upload do certificado: {e}")
            raise HTTPException(status_code=500, detail="Erro ao processar certificado")
    
    async def get_certificate(
        self,
        company_id: int
    ) -> Optional[CompanyCertificate]:
        """Busca o certificado de uma empresa"""
        result = await self.db.execute(
            select(CompanyCertificate).where(
                CompanyCertificate.company_id == company_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_certificate_data(
        self,
        cert: CompanyCertificate
    ) -> Tuple[bytes, str]:
        """
        Carrega os dados do certificado do storage e descriptografa a senha
        
        Args:
            cert: CompanyCertificate
            
        Returns:
            (pfx_data_bytes, password)
        """
        try:
            # Baixa o .pfx do storage
            pfx_data = self.storage.get_object(cert.cert_storage_key)
            
            # Descriptografa a senha
            password = self.crypto.decrypt(cert.cert_password_enc)
            
            return pfx_data, password
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados do certificado: {e}")
            raise
    
    async def update_certificate_status(
        self,
        company_id: int,
        status: str,
        error: Optional[str] = None
    ):
        """Atualiza o status de um certificado"""
        cert = await self.get_certificate(company_id)
        if cert:
            cert.status = status
            cert.last_error = error
            cert.updated_at = datetime.utcnow()
            await self.db.commit()
    
    async def check_and_update_expired_certificates(self):
        """Job para verificar e marcar certificados expirados"""
        result = await self.db.execute(
            select(CompanyCertificate).where(
                CompanyCertificate.status == "active"
            )
        )
        certificates = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        for cert in certificates:
            if now > cert.valid_to:
                cert.status = "expired"
                cert.last_error = f"Certificado expirado em {cert.valid_to}"
                cert.updated_at = datetime.utcnow()
                logger.warning(f"Certificado da empresa {cert.company_id} expirado")
        
        await self.db.commit()
