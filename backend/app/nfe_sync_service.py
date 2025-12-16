"""
Serviço de sincronização e parsing de NF-e
"""
from datetime import datetime, timezone
import logging
import hashlib
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.models import (
    Company, CompanyCertificate, SefazDfeState,
    NfeDocument, NfeSyncLog
)
from app.sefaz_client import SefazDFeClient, DFeDocument
from app.certificate_service import CertificateService
from app.storage import MinIOService as StorageService
from app.config import settings

logger = logging.getLogger(__name__)


class NfeParserService:
    """Serviço para fazer parse de XMLs de NF-e"""
    
    NS_NFE = "{http://www.portalfiscal.inf.br/nfe}"
    
    @staticmethod
    def parse_nfe_xml(xml_content: str, company_cnpj: str) -> Dict[str, Any]:
        """
        Faz parse do XML da NF-e e extrai campos principais
        
        Args:
            xml_content: XML da NF-e
            company_cnpj: CNPJ da empresa dona do certificado
            
        Returns:
            Dict com campos extraídos
        """
        try:
            root = ET.fromstring(xml_content)
            ns = NfeParserService.NS_NFE
            
            # Extrai chave
            inf_nfe = root.find(f'.//{ns}infNFe')
            chave = ""
            if inf_nfe is not None:
                id_attr = inf_nfe.get('Id', '')
                if id_attr.startswith('NFe'):
                    chave = id_attr[3:]
            
            # Extrai dados da NF-e
            ide = root.find(f'.//{ns}ide')
            emit = root.find(f'.//{ns}emit')
            dest = root.find(f'.//{ns}dest')
            total = root.find(f'.//{ns}total/{ns}ICMSTot')
            
            # Número e série
            numero = ide.find(f'{ns}nNF').text if ide is not None and ide.find(f'{ns}nNF') is not None else None
            serie = ide.find(f'{ns}serie').text if ide is not None and ide.find(f'{ns}serie') is not None else None
            
            # Data de emissão
            data_emissao = None
            if ide is not None:
                dh_emi = ide.find(f'{ns}dhEmi')
                if dh_emi is not None:
                    try:
                        data_emissao = datetime.fromisoformat(dh_emi.text.replace('Z', '+00:00'))
                    except:
                        pass
            
            # Emitente
            cnpj_emitente = emit.find(f'{ns}CNPJ').text if emit is not None and emit.find(f'{ns}CNPJ') is not None else None
            emitente_nome = emit.find(f'{ns}xNome').text if emit is not None and emit.find(f'{ns}xNome') is not None else None
            
            # Destinatário
            cnpj_destinatario = None
            destinatario_nome = None
            if dest is not None:
                cnpj_dest = dest.find(f'{ns}CNPJ')
                if cnpj_dest is not None:
                    cnpj_destinatario = cnpj_dest.text
                nome_dest = dest.find(f'{ns}xNome')
                if nome_dest is not None:
                    destinatario_nome = nome_dest.text
            
            # Valor total
            valor_total = None
            if total is not None:
                v_nf = total.find(f'{ns}vNF')
                if v_nf is not None:
                    try:
                        valor_total = float(v_nf.text)
                    except:
                        pass
            
            # Determina tipo (recebida, emitida, desconhecida)
            tipo = "desconhecida"
            if cnpj_emitente and cnpj_destinatario:
                company_cnpj_clean = company_cnpj.replace(".", "").replace("/", "").replace("-", "")
                if cnpj_emitente == company_cnpj_clean:
                    tipo = "emitida"
                elif cnpj_destinatario == company_cnpj_clean:
                    tipo = "recebida"
            
            return {
                'chave': chave,
                'numero': numero,
                'serie': serie,
                'data_emissao': data_emissao,
                'cnpj_emitente': cnpj_emitente,
                'emitente_nome': emitente_nome,
                'cnpj_destinatario': cnpj_destinatario,
                'destinatario_nome': destinatario_nome,
                'valor_total': valor_total,
                'tipo': tipo,
                'situacao': 'autorizada'  # Se está no DF-e, está autorizada
            }
            
        except Exception as e:
            logger.error(f"Erro ao fazer parse do XML: {e}")
            return {
                'chave': '',
                'tipo': 'desconhecida',
                'situacao': 'desconhecida'
            }


class NfeSyncService:
    """Serviço de sincronização de NF-e com SEFAZ"""
    
    def __init__(
        self,
        db: AsyncSession,
        cert_service: CertificateService,
        storage: StorageService
    ):
        self.db = db
        self.cert_service = cert_service
        self.storage = storage
    
    async def sync_company(
        self,
        company_id: int,
        sync_type: str = "incremental"
    ) -> Dict[str, Any]:
        """
        Sincroniza NF-e de uma empresa
        
        Args:
            company_id: ID da empresa
            sync_type: incremental, manual
            
        Returns:
            Dict com resultado da sincronização
        """
        log = None
        try:
            # Verifica se a empresa existe
            company_result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = company_result.scalar_one_or_none()
            if not company:
                return {
                    'company_id': company_id,
                    'status': 'error',
                    'error_message': 'Empresa não encontrada',
                    'docs_found': 0,
                    'docs_imported': 0
                }
            
            # Busca o certificado
            cert = await self.cert_service.get_certificate(company_id)
            if not cert or cert.status != 'active':
                return {
                    'company_id': company_id,
                    'status': 'error',
                    'error_message': 'Certificado não encontrado ou inativo',
                    'docs_found': 0,
                    'docs_imported': 0
                }
            
            # Cria log de sincronização
            log = NfeSyncLog(
                company_id=company_id,
                sync_type=sync_type,
                started_at=datetime.utcnow(),
                status='running'
            )
            self.db.add(log)
            await self.db.commit()
            
            # Carrega dados do certificado
            pfx_data, password = await self.cert_service.get_certificate_data(cert)
            
            # Obtém código IBGE da UF da empresa (se disponível)
            uf_code = None
            if hasattr(company, 'codigo_ibge_uf') and company.codigo_ibge_uf:
                uf_code = company.codigo_ibge_uf
                logger.info(f"🔍 Usando UF da empresa: {company.uf} = {uf_code}")
            
            # Inicializa cliente SEFAZ
            sefaz_client = SefazDFeClient(
                cnpj=cert.cnpj,
                cert_pfx_data=pfx_data,
                cert_password=password,
                producao=settings.NFE_AMBIENTE_PRODUCAO,
                uf_code=uf_code
            )
            
            # Busca ou cria estado de sincronização
            state_result = await self.db.execute(
                select(SefazDfeState).where(SefazDfeState.company_id == company_id)
            )
            state = state_result.scalar_one_or_none()
            
            if not state:
                state = SefazDfeState(
                    company_id=company_id,
                    last_nsu="0",
                    last_status="ok"
                )
                self.db.add(state)
                await self.db.commit()

            # Anti-bloqueio: se último cStat foi 137 e há menos de 1h, evita nova chamada
            if state.last_cstat == '137' and state.last_sync_at:
                delta = datetime.utcnow() - state.last_sync_at
                if delta.total_seconds() < 3600:
                    logger.info(
                        "skip_sync_cstat_137_recent",
                        extra={"company_id": company_id, "minutes_ago": round(delta.total_seconds() / 60, 1)}
                    )
                    return {
                        'company_id': company_id,
                        'status': 'partial',
                        'docs_found': 0,
                        'docs_imported': 0,
                        'last_nsu': state.last_nsu,
                        'error_message': 'Último cStat=137 há menos de 1h'
                    }
            
            # Consulta SEFAZ
            ultimo_nsu = state.last_nsu
            response = await sefaz_client.consultar_distribuicao(ultimo_nsu=ultimo_nsu)

            logger.info(
                "SEFAZ resposta",
                extra={
                    "company_id": company_id,
                    "status": response.get("status"),
                    "motivo": response.get("motivo"),
                    "max_nsu": response.get("max_nsu"),
                    "ult_nsu": response.get("ult_nsu"),
                    "docs": len(response.get("documentos", [])),
                },
            )
            
            # Processa documentos
            docs_found = len(response['documentos'])
            docs_imported = 0
            full_doc_cache: Dict[str, DFeDocument] = {}
            
            for doc in response['documentos']:
                try:
                    resolved_doc = await self._resolve_full_document(
                        sefaz_client=sefaz_client,
                        original_doc=doc,
                        cache=full_doc_cache
                    )
                    imported = await self._process_document(
                        company_id=company_id,
                        company_cnpj=cert.cnpj,
                        doc=resolved_doc
                    )
                    if imported:
                        docs_imported += 1
                except Exception as e:
                    logger.error(f"Erro ao processar documento NSU {doc.nsu}: {e}")
            
            # Atualiza estado
            state.last_cstat = str(response.get('status')) if response.get('status') is not None else state.last_cstat
            if response['status'] in [137, 138]:  # Sucesso ou sem novos docs
                state.last_nsu = response['max_nsu'] if response['status'] == 138 else state.last_nsu
                state.last_sync_at = datetime.utcnow()
                state.last_status = "ok"
                state.last_error = None
            else:
                state.last_status = "error"
                state.last_error = response['motivo']
            
            await self.db.commit()
            
            # Atualiza log
            log.finished_at = datetime.utcnow()
            log.status = 'success' if response['status'] == 138 else 'partial'
            log.docs_found = docs_found
            log.docs_imported = docs_imported
            await self.db.commit()
            
            logger.info(
                f"Sync empresa {company_id}: {docs_imported}/{docs_found} docs importados",
                extra={"cStat": response.get('status'), "motivo": response.get('motivo')}
            )
            
            return {
                'company_id': company_id,
                'status': 'success' if response['status'] == 138 else 'partial',
                'docs_found': docs_found,
                'docs_imported': docs_imported,
                'last_nsu': response['max_nsu'],
                'error_message': None
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar empresa {company_id}: {e}")
            
            # Recupera último NSU conhecido para responder ao cliente
            last_nsu = "0"
            try:
                state_result = await self.db.execute(
                    select(SefazDfeState).where(SefazDfeState.company_id == company_id)
                )
                existing_state = state_result.scalar_one_or_none()
                if existing_state:
                    last_nsu = existing_state.last_nsu or "0"
            except Exception:
                pass
            
            # Atualiza log como erro
            if log:
                log.finished_at = datetime.utcnow()
                log.status = 'error'
                log.error_message = str(e)
                await self.db.commit()
            
            return {
                'company_id': company_id,
                'status': 'error',
                'error_message': str(e),
                'docs_found': 0,
                'docs_imported': 0,
                'last_nsu': last_nsu
            }
    
    async def _process_document(
        self,
        company_id: int,
        company_cnpj: str,
        doc: DFeDocument
    ) -> bool:
        """Processa e salva um documento"""
        try:
            existing_result = await self.db.execute(
                select(NfeDocument).where(NfeDocument.chave == doc.chave)
            )
            existing = existing_result.scalar_one_or_none()

            parsed = NfeParserService.parse_nfe_xml(doc.xml_content, company_cnpj)
            xml_kind = 'full' if 'procNFe' in (doc.schema or '') else 'summary'

            year = datetime.now().year
            month = datetime.now().month
            storage_key = f"nfe/xml/{company_id}/{company_cnpj}/{year}/{month:02d}/{doc.chave}.xml"

            self.storage.put_object(
                storage_key,
                doc.xml_content.encode('utf-8'),
                "application/xml"
            )

            xml_sha256 = hashlib.sha256(doc.xml_content.encode('utf-8')).hexdigest()

            if existing:
                if existing.xml_kind == 'summary' and xml_kind == 'full':
                    logger.info(f"Atualizando XML completo para {doc.chave}")
                    existing.xml_storage_key = storage_key
                    existing.xml_sha256 = xml_sha256
                    existing.xml_kind = xml_kind
                    existing.updated_at = datetime.utcnow()
                    existing.numero = parsed.get('numero')
                    existing.serie = parsed.get('serie')
                    existing.data_emissao = parsed.get('data_emissao')
                    existing.cnpj_emitente = parsed.get('cnpj_emitente')
                    existing.emitente_nome = parsed.get('emitente_nome')
                    existing.cnpj_destinatario = parsed.get('cnpj_destinatario')
                    existing.destinatario_nome = parsed.get('destinatario_nome')
                    existing.valor_total = parsed.get('valor_total')
                    existing.tipo = parsed.get('tipo') or existing.tipo
                    existing.situacao = parsed.get('situacao') or existing.situacao
                    await self.db.commit()
                    return True
                logger.debug(f"Documento {doc.chave} já existe, pulando")
                return False

            nfe_doc = NfeDocument(
                company_id=company_id,
                chave=doc.chave or parsed['chave'],
                nsu=doc.nsu,
                tipo=parsed['tipo'],
                situacao=parsed['situacao'],
                numero=parsed.get('numero'),
                serie=parsed.get('serie'),
                data_emissao=parsed.get('data_emissao'),
                cnpj_emitente=parsed.get('cnpj_emitente'),
                emitente_nome=parsed.get('emitente_nome'),
                cnpj_destinatario=parsed.get('cnpj_destinatario'),
                destinatario_nome=parsed.get('destinatario_nome'),
                valor_total=parsed.get('valor_total'),
                xml_storage_key=storage_key,
                xml_sha256=xml_sha256,
                xml_kind=xml_kind,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(nfe_doc)
            await self.db.commit()

            logger.info(f"Documento {doc.chave} importado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao processar documento: {e}")
            return False

    async def _resolve_full_document(
        self,
        sefaz_client: SefazDFeClient,
        original_doc: DFeDocument,
        cache: Dict[str, DFeDocument],
        allow_refetch: bool = True
    ) -> DFeDocument:
        """Tenta substituir resNFe por procNFe para evitar PDFs incompletos."""
        chave = original_doc.chave

        if not chave:
            return original_doc

        if chave in cache:
            return cache[chave]

        if 'resNFe' not in (original_doc.schema or '') or not allow_refetch:
            cache[chave] = original_doc
            return original_doc

        try:
            logger.info(f"🔁 Buscando XML completo para chave {chave}")
            response = await sefaz_client.consultar_por_chave(chave)
            full_doc = next(
                (
                    d for d in response.get('documentos', [])
                    if 'procNFe' in (d.schema or '')
                ),
                None
            )

            if full_doc:
                cache[chave] = full_doc
                logger.info(f"✅ XML completo encontrado para chave {chave}")
                return full_doc

        except Exception as e:
            logger.warning(f"⚠️ Falha ao buscar XML completo para {chave}: {e}")

        cache[chave] = original_doc
        return original_doc
    
    async def import_by_key(
        self,
        company_id: int,
        chave: str
    ) -> Dict[str, Any]:
        """Importa uma NF-e específica por chave de acesso"""
        try:
            # Busca a empresa
            company_result = await self.db.execute(
                select(Company).where(Company.id == company_id)
            )
            company = company_result.scalar_one_or_none()
            
            # Busca certificado
            cert = await self.cert_service.get_certificate(company_id)
            if not cert or cert.status != 'active':
                return {
                    'status': 'error',
                    'error_message': 'Certificado não encontrado ou inativo'
                }
            
            # Carrega dados do certificado
            pfx_data, password = await self.cert_service.get_certificate_data(cert)
            
            # Obtém código IBGE da UF da empresa (se disponível)
            uf_code = None
            if company and hasattr(company, 'codigo_ibge_uf') and company.codigo_ibge_uf:
                uf_code = company.codigo_ibge_uf
            
            # Inicializa cliente SEFAZ
            sefaz_client = SefazDFeClient(
                cnpj=cert.cnpj,
                cert_pfx_data=pfx_data,
                cert_password=password,
                producao=settings.NFE_AMBIENTE_PRODUCAO,
                uf_code=uf_code
            )
            
            # Consulta por chave
            response = await sefaz_client.consultar_por_chave(chave)
            
            # Processa documentos
            docs_imported = 0
            cache: Dict[str, DFeDocument] = {}
            for doc in response['documentos']:
                resolved_doc = await self._resolve_full_document(
                    sefaz_client=sefaz_client,
                    original_doc=doc,
                    cache=cache,
                    allow_refetch=False
                )
                imported = await self._process_document(
                    company_id=company_id,
                    company_cnpj=cert.cnpj,
                    doc=resolved_doc
                )
                if imported:
                    docs_imported += 1
            
            return {
                'status': 'success',
                'docs_found': len(response['documentos']),
                'docs_imported': docs_imported
            }
            
        except Exception as e:
            logger.error(f"Erro ao importar por chave: {e}")
            return {
                'status': 'error',
                'error_message': str(e)
            }
