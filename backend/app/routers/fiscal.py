"""
Rotas da API para o módulo fiscal (certificados e NF-e)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Company, CompanyCertificate, NfeDocument, SefazDfeState, NfeSyncLog
from app.schemas_fiscal import (
    CertificateResponse, CertificateUpdate,
    NfeDocumentResponse, NfeDocumentFilter,
    SyncRequest, SyncResponse, ImportByKeyRequest,
    SefazDfeStateResponse, NfeSyncLogResponse, NfeSyncLogFilter,
    ResolveResponse
)
from app.certificate_service import CertificateService
from app.nfe_sync_service import NfeSyncService
from app.storage import MinIOService as StorageService
from app.crypto_service import CryptoService
from app.config import settings
from app.manifestacao_service import ManifestacaoService

import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fiscal", tags=["fiscal"])


def _parse_resnfe(xml_content: str) -> dict:
    """Extrai campos básicos de um XML resumido (resNFe)."""
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    root = ET.fromstring(xml_content)

    def _find_text(path: str) -> str:
        el = root.find(path, ns)
        return el.text if el is not None and el.text else ''

    tp_nf = _find_text('.//nfe:tpNF')
    situacao_code = _find_text('.//nfe:cSitNFe')

    situacao_map = {
        '1': 'autorizada',
        '2': 'denegada',
        '3': 'cancelada',
    }

    tipo = 'emitida' if tp_nf == '1' else 'recebida'

    return {
        'chave': _find_text('.//nfe:chNFe'),
        'emitente_nome': _find_text('.//nfe:xNome'),
        'cnpj_emitente': _find_text('.//nfe:CNPJ'),
        'data_emissao': _find_text('.//nfe:dhEmi'),
        'valor_total': _find_text('.//nfe:vNF'),
        'tipo': tipo,
        'situacao': situacao_map.get(situacao_code, 'desconhecida'),
    }


def _enrich_documents_with_xml(documents: list, storage: StorageService):
    """Preenche campos vazios a partir do XML resumido armazenado no MinIO."""
    for doc in documents:
        needs_enrich = any([
            not doc.emitente_nome,
            not doc.cnpj_emitente,
            not doc.data_emissao,
            not doc.valor_total,
            not doc.tipo or doc.tipo == 'desconhecida',
            not doc.situacao or doc.situacao == 'desconhecida',
        ])
        if not needs_enrich:
            continue
        try:
            xml_bytes = storage.get_object(doc.xml_storage_key)
            info = _parse_resnfe(xml_bytes.decode('utf-8'))
            doc.emitente_nome = info.get('emitente_nome') or doc.emitente_nome
            doc.cnpj_emitente = info.get('cnpj_emitente') or doc.cnpj_emitente
            if info.get('data_emissao'):
                try:
                    doc.data_emissao = datetime.fromisoformat(info['data_emissao'].replace('Z', '+00:00'))
                except Exception:
                    pass
            try:
                doc.valor_total = float(info['valor_total']) if info.get('valor_total') else doc.valor_total
            except Exception:
                pass
            doc.tipo = info.get('tipo') or doc.tipo
            doc.situacao = info.get('situacao') or doc.situacao
        except Exception as e:
            logger.warning(f"Falha ao enriquecer NF-e {doc.id}: {e}")


# ==================== CERTIFICADOS ====================

@router.post("/companies/{company_id}/certificate", response_model=CertificateResponse)
async def upload_certificate(
    company_id: int,
    file: UploadFile = File(..., description="Arquivo .pfx do certificado"),
    password: str = Form(..., description="Senha do certificado"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload de certificado digital A1 para uma empresa"""
    # Validações de arquivo
    if not file.filename.endswith('.pfx'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .pfx")
    
    # Inicializa serviços
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    
    # Faz upload do certificado
    certificate = await cert_service.upload_certificate(company_id, file, password)
    
    return certificate


@router.get("/companies/{company_id}/certificate", response_model=CertificateResponse)
async def get_certificate(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Busca o certificado de uma empresa"""
    result = await db.execute(
        select(CompanyCertificate).where(
            CompanyCertificate.company_id == company_id
        )
    )
    certificate = result.scalar_one_or_none()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    
    return certificate


@router.get("/companies/{company_id}/certificate/info")
async def get_certificate_info(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Busca informações detalhadas do certificado para diagnóstico.
    Retorna: CNPJ, UF detectado, validade, subject, etc.
    """
    from app.sefaz_client import SefazDFeClient
    
    # Busca a empresa
    company_result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = company_result.scalar_one_or_none()
    
    # Busca certificado
    result = await db.execute(
        select(CompanyCertificate).where(
            CompanyCertificate.company_id == company_id
        )
    )
    certificate = result.scalar_one_or_none()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    
    # Inicializa serviços
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    
    # Carrega dados do certificado
    pfx_data, password = await cert_service.get_certificate_data(certificate)
    
    # Obtém código IBGE da UF da empresa (se disponível)
    uf_code_from_company = None
    if company and hasattr(company, 'codigo_ibge_uf') and company.codigo_ibge_uf:
        uf_code_from_company = company.codigo_ibge_uf
    
    # Cria cliente SEFAZ apenas para extrair informações
    sefaz_client = SefazDFeClient(
        cnpj=certificate.cnpj,
        cert_pfx_data=pfx_data,
        cert_password=password,
        producao=settings.NFE_AMBIENTE_PRODUCAO,
        uf_code=uf_code_from_company
    )
    
    # Extrai informações do certificado
    from cryptography import x509
    cert_x509 = sefaz_client.certificate
    subject = cert_x509.subject
    
    # Extrai campos do subject
    subject_dict = {}
    uf_detected = None
    for attr in subject:
        key = attr.oid._name
        value = str(attr.value)
        subject_dict[key] = value
        
        if key in ['stateOrProvinceName', 'ST']:
            uf_detected = value.upper()
    
    # Mapeia UF para código IBGE
    uf_code_from_cert = sefaz_client.UF_CODES.get(uf_detected, "91") if uf_detected else "91"
    
    return {
        "company_id": company_id,
        "cnpj": certificate.cnpj,
        "status": certificate.status,
        "valid_from": cert_x509.not_valid_before.isoformat(),
        "valid_until": cert_x509.not_valid_after.isoformat(),
        "uf_detected_from_cert": uf_detected,
        "uf_code_from_cert": uf_code_from_cert,
        "uf_from_company": company.uf if company else None,
        "uf_code_from_company": uf_code_from_company,
        "uf_code_used": sefaz_client.uf_code,
        "subject": subject_dict,
        "issuer": cert_x509.issuer.rfc4514_string(),
        "ambiente": "PRODUÇÃO" if settings.NFE_AMBIENTE_PRODUCAO else "HOMOLOGAÇÃO",
    }


@router.patch("/companies/{company_id}/certificate", response_model=CertificateResponse)
async def update_certificate(
    company_id: int,
    data: CertificateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Atualiza o status de um certificado"""
    result = await db.execute(
        select(CompanyCertificate).where(
            CompanyCertificate.company_id == company_id
        )
    )
    certificate = result.scalar_one_or_none()
    
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    
    if data.status:
        certificate.status = data.status
        certificate.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(certificate)
    
    return certificate


# ==================== SINCRONIZAÇÃO ====================

@router.post("/nfe/sync", response_model=List[SyncResponse])
async def sync_all_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sincroniza NF-e de todas as empresas com certificado ativo"""
    # Busca todas as empresas com certificado ativo
    result = await db.execute(
        select(CompanyCertificate).where(
            CompanyCertificate.status == 'active'
        )
    )
    certificates = result.scalars().all()
    
    # Inicializa serviços
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    sync_service = NfeSyncService(db, cert_service, storage)
    
    # Sincroniza cada empresa
    results = []
    for cert in certificates:
        try:
            sync_result = await sync_service.sync_company(cert.company_id, sync_type="manual")
            results.append(SyncResponse(**sync_result))
        except Exception as e:
            logger.error(f"Erro ao sincronizar empresa {cert.company_id}: {e}")
            results.append(SyncResponse(
                company_id=cert.company_id,
                status='error',
                docs_found=0,
                docs_imported=0,
                last_nsu='0',
                error_message=str(e)
            ))
    
    return results


@router.post("/nfe/sync/{company_id}", response_model=SyncResponse)
async def sync_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sincroniza NF-e de uma empresa específica"""
    # Inicializa serviços
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    sync_service = NfeSyncService(db, cert_service, storage)
    
    # Sincroniza
    sync_result = await sync_service.sync_company(company_id, sync_type="manual")
    
    return SyncResponse(**sync_result)


@router.post("/nfe/resolve/{company_id}", response_model=ResolveResponse)
async def resolve_company_xml(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Tenta manifestar e baixar XML completo das NF-e resumidas de uma empresa"""
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    manifest_service = ManifestacaoService(db, cert_service, storage)

    result = await manifest_service.resolve_company(company_id)
    return ResolveResponse(**result)


@router.post("/nfe/resolve/{company_id}/{chave}", response_model=ResolveResponse)
async def resolve_single_xml(
    company_id: int,
    chave: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve XML completo para uma chave específica"""
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    manifest_service = ManifestacaoService(db, cert_service, storage)

    result = await manifest_service.resolve_document(company_id, chave)
    attempted = 1
    resolved = 1 if result.get("status") == "full" else 0
    still_summary = attempted - resolved
    return ResolveResponse(company_id=company_id, attempted=attempted, resolved=resolved, still_summary=still_summary, errors=None)


@router.get("/nfe/state/{company_id}", response_model=SefazDfeStateResponse)
async def get_sync_state(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Busca o estado de sincronização de uma empresa"""
    result = await db.execute(
        select(SefazDfeState).where(SefazDfeState.company_id == company_id)
    )
    state = result.scalar_one_or_none()
    
    if not state:
        raise HTTPException(status_code=404, detail="Estado de sincronização não encontrado")
    
    return state


# ==================== NOTAS FISCAIS ====================

@router.get("/nfe", response_model=List[NfeDocumentResponse])
async def list_nfe_documents(
    company_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    data_ini: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None),
    emitente: Optional[str] = Query(None),
    valor_min: Optional[float] = Query(None),
    valor_max: Optional[float] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lista documentos NF-e com filtros"""
    # Constrói query
    query = select(NfeDocument)
    
    # Aplica filtros
    conditions = []
    if company_id:
        conditions.append(NfeDocument.company_id == company_id)
    if tipo:
        conditions.append(NfeDocument.tipo == tipo)
    if data_ini:
        conditions.append(NfeDocument.data_emissao >= data_ini)
    if data_fim:
        conditions.append(NfeDocument.data_emissao <= data_fim)
    if emitente:
        conditions.append(
            or_(
                NfeDocument.emitente_nome.ilike(f"%{emitente}%"),
                NfeDocument.cnpj_emitente.ilike(f"%{emitente}%")
            )
        )
    if valor_min:
        conditions.append(NfeDocument.valor_total >= valor_min)
    if valor_max:
        conditions.append(NfeDocument.valor_total <= valor_max)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Ordena por data de emissão decrescente
    query = query.order_by(NfeDocument.data_emissao.desc())
    
    # Paginação
    query = query.offset(skip).limit(limit)
    
    # Executa
    result = await db.execute(query)
    documents = result.scalars().all()

    # Enriquecimento com XML resumido (resNFe) para preencher campos faltantes
    storage = StorageService()
    _enrich_documents_with_xml(documents, storage)
    
    return documents


@router.get("/nfe/{nfe_id}", response_model=NfeDocumentResponse)
async def get_nfe_document(
    nfe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Busca um documento NF-e por ID"""
    result = await db.execute(
        select(NfeDocument).where(NfeDocument.id == nfe_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    return document


@router.get("/nfe/{nfe_id}/xml")
async def download_nfe_xml(
    nfe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Gera URL de download do XML da NF-e"""
    result = await db.execute(
        select(NfeDocument).where(NfeDocument.id == nfe_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Gera URL presigned (válida por 1 hora)
    storage = StorageService()
    url = await storage.generate_presigned_url(
        document.xml_storage_key,
        expires_in=3600
    )
    
    return {"download_url": url}


@router.get("/nfe/{nfe_id}/pdf")
async def download_nfe_pdf(
    nfe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Gera PDF (DANFE) da NF-e"""
    from fastapi.responses import StreamingResponse
    from app.services.nfe_pdf_generator import NFePDFGenerator
    
    # Busca documento
    result = await db.execute(
        select(NfeDocument).where(NfeDocument.id == nfe_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Baixa XML do storage
    storage = StorageService()
    xml_content = await storage.download_file(document.xml_storage_key)

    # Evita gerar PDF de XML resumido (resNFe)
    if xml_content.startswith(b"<resNFe"):
        raise HTTPException(status_code=400, detail="Este XML é um resumo (resNFe) e não contém dados suficientes para gerar DANFE")
    
    # Gera PDF
    try:
        pdf_generator = NFePDFGenerator()
        pdf_buffer = pdf_generator.generate_pdf(xml_content.decode('utf-8'))
        
        # Retorna PDF
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=NF-e_{document.numero}_{document.serie}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")


@router.get("/nfe/{nfe_id}/xml-content")
async def get_nfe_xml_content(
    nfe_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retorna o conteúdo do XML da NF-e para visualização"""
    result = await db.execute(
        select(NfeDocument).where(NfeDocument.id == nfe_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Baixa XML do storage
    storage = StorageService()
    xml_content = await storage.download_file(document.xml_storage_key)
    
    return {"xml_content": xml_content.decode('utf-8')}


@router.post("/nfe/import-by-key")
async def import_by_key(
    data: ImportByKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Importa uma NF-e específica pela chave de acesso"""
    # Inicializa serviços
    storage = StorageService()
    crypto = CryptoService(settings.CERT_MASTER_KEY)
    cert_service = CertificateService(db, storage, crypto)
    sync_service = NfeSyncService(db, cert_service, storage)
    
    # Importa
    result = await sync_service.import_by_key(data.company_id, data.chave)
    
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['error_message'])
    
    return result


# ==================== LOGS ====================

@router.get("/nfe/logs", response_model=List[NfeSyncLogResponse])
async def list_sync_logs(
    company_id: Optional[int] = Query(None),
    sync_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lista logs de sincronização"""
    query = select(NfeSyncLog)
    
    conditions = []
    if company_id:
        conditions.append(NfeSyncLog.company_id == company_id)
    if sync_type:
        conditions.append(NfeSyncLog.sync_type == sync_type)
    if status:
        conditions.append(NfeSyncLog.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(NfeSyncLog.started_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs
