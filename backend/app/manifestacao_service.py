"""
Serviço para manifestação do destinatário e resolução de XML completo
"""
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Company, NfeDocument, NfeManifestation
from app.sefaz_client import SefazDFeClient, DFeDocument
from app.sefaz_evento_client import SefazEventoClient
from app.certificate_service import CertificateService
from app.storage import MinIOService as StorageService
from app.config import settings
from app.nfe_sync_service import NfeParserService

logger = logging.getLogger(__name__)


class ManifestacaoService:
    def __init__(self, db: AsyncSession, cert_service: CertificateService, storage: StorageService):
        self.db = db
        self.cert_service = cert_service
        self.storage = storage

    async def _get_company_and_cert(self, company_id: int):
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError("Empresa não encontrada")

        cert = await self.cert_service.get_certificate(company_id)
        if not cert or cert.status != 'active':
            raise ValueError("Certificado não encontrado ou inativo")
        return company, cert

    async def _ensure_manifest_record(self, company_id: int, chave: str, tp_evento: str) -> NfeManifestation:
        result = await self.db.execute(
            select(NfeManifestation).where(
                NfeManifestation.company_id == company_id,
                NfeManifestation.chave == chave,
                NfeManifestation.tp_evento == tp_evento,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.tentativas = (record.tentativas or 0) + 1
            record.last_attempt_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            return record
        record = NfeManifestation(
            company_id=company_id,
            chave=chave,
            tp_evento=tp_evento,
            status="pending",
            tentativas=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_attempt_at=datetime.utcnow(),
        )
        self.db.add(record)
        return record

    async def _save_document(self, company_id: int, company_cnpj: str, doc: DFeDocument, xml_kind: str) -> bool:
        parsed = NfeParserService.parse_nfe_xml(doc.xml_content, company_cnpj)
        year = datetime.utcnow().year
        month = datetime.utcnow().month
        storage_key = f"nfe/xml/{company_id}/{company_cnpj}/{year}/{month:02d}/{doc.chave}.xml"

        self.storage.put_object(storage_key, doc.xml_content.encode('utf-8'), "application/xml")
        xml_sha256 = self.storage.calculate_sha256(doc.xml_content.encode('utf-8'))

        existing_result = await self.db.execute(select(NfeDocument).where(NfeDocument.chave == doc.chave))
        existing = existing_result.scalar_one_or_none()

        if existing:
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
        else:
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
                updated_at=datetime.utcnow(),
            )
            self.db.add(nfe_doc)
        await self.db.commit()
        return True

    async def _try_fetch_full(self, company_id: int, company_cnpj: str, sefaz_client: SefazDFeClient, chave: str) -> Optional[DFeDocument]:
        response = await sefaz_client.consultar_por_chave(chave)
        for doc in response.get('documentos', []):
            if 'procNFe' in (doc.schema or ''):
                await self._save_document(company_id, company_cnpj, doc, xml_kind='full')
                return doc
        # se só resumo, salvar/atualizar summary
        for doc in response.get('documentos', []):
            if 'resNFe' in (doc.schema or ''):
                await self._save_document(company_id, company_cnpj, doc, xml_kind='summary')
                return None
        return None

    async def resolve_document(self, company_id: int, chave: str, tp_evento: str = "210210") -> Dict[str, Any]:
        print(f"🚀 [DEBUG] resolve_document chamado: company_id={company_id}, chave={chave}")
        company, cert = await self._get_company_and_cert(company_id)
        pfx_data, password = await self.cert_service.get_certificate_data(cert)

        # Pega UF da empresa ou usa padrão GO
        uf = company.uf if hasattr(company, 'uf') and company.uf else "GO"
        
        sefaz_dist = SefazDFeClient(
            cnpj=cert.cnpj,
            cert_pfx_data=pfx_data,
            cert_password=password,
            producao=settings.NFE_AMBIENTE_PRODUCAO,
        )
        evento_client = SefazEventoClient(
            cnpj=cert.cnpj,
            cert_pfx_data=pfx_data,
            cert_password=password,
            producao=settings.NFE_AMBIENTE_PRODUCAO,
            uf=uf,  # Passa UF em vez de uf_code
        )

        # Passo 1: tentar já obter completo
        print(f"🔍 [MANIFESTAÇÃO] Passo 1: Tentando obter XML completo para chave {chave}")
        doc_full = await self._try_fetch_full(company_id, cert.cnpj, sefaz_dist, chave)
        if doc_full:
            print(f"✅ [MANIFESTAÇÃO] XML completo já disponível para {chave}")
            return {"status": "full", "chave": chave}
        print(f"⏭️  [MANIFESTAÇÃO] XML completo não disponível, seguindo para manifestação")

        # Passo 2: manifestar
        print(f"📝 [MANIFESTAÇÃO] Passo 2: Criando registro de manifestação")
        manifest_record = await self._ensure_manifest_record(company_id, chave, tp_evento)
        await self.db.commit()
        
        try:
            print(f"📤 [MANIFESTAÇÃO] Iniciando manifestação: chave={chave}, tp_evento={tp_evento}, uf={uf}")
            result = await evento_client.manifestar(chave, tp_evento=tp_evento)
            print(f"📥 [MANIFESTAÇÃO] Manifestação retornou: {result}")
            evento_info = result.get("evento", {})
            manifest_record.status = "accepted" if evento_info.get("cStat") in ["135", "128"] else "sent"
            manifest_record.protocolo = evento_info.get("nProt")
            manifest_record.dh_evento = datetime.utcnow()
            manifest_record.last_error = None
            manifest_record.updated_at = datetime.utcnow()
        except Exception as e:
            print(f"❌ [MANIFESTAÇÃO] Erro na manifestação: {e}")
            logger.error(f"❌ Erro na manifestação: {e}", exc_info=True)
            manifest_record.status = "error"
            manifest_record.last_error = str(e)[:500]
            manifest_record.updated_at = datetime.utcnow()
        
        await self.db.commit()

        # Passo 3: reconsultar
        print(f"🔄 [MANIFESTAÇÃO] Passo 3: Reconsultando após manifestação")
        max_attempts = 3
        for attempt in range(max_attempts):
            fetched = await self._try_fetch_full(company_id, cert.cnpj, sefaz_dist, chave)
            if fetched:
                return {"status": "full", "chave": chave}
            await asyncio.sleep(2)

        manifest_record.status = "pending"
        manifest_record.last_error = "Ainda não retornou procNFe"
        manifest_record.updated_at = datetime.utcnow()
        await self.db.commit()
        return {"status": "summary", "chave": chave}

    async def resolve_company(self, company_id: int, limit: int = 50) -> Dict[str, Any]:
        result = await self.db.execute(
            select(NfeDocument).where(
                NfeDocument.company_id == company_id,
                NfeDocument.xml_kind == 'summary'
            ).limit(limit)
        )
        docs = result.scalars().all()
        resolved = 0
        errors = []
        for doc in docs:
            try:
                outcome = await self.resolve_document(company_id, doc.chave)
                if outcome.get("status") == "full":
                    resolved += 1
            except Exception as e:
                logger.error("resolve_document_failed", extra={"chave": doc.chave, "error": str(e)})
                errors.append(f"{doc.chave}: {e}")
        return {
            "company_id": company_id,
            "attempted": len(docs),
            "resolved": resolved,
            "still_summary": len(docs) - resolved,
            "errors": "; ".join(errors) if errors else None,
        }
