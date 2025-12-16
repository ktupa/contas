from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.models_signatures import SignatureDocument, SignatureSigner
from app.services.pdf_generator import generate_receipt_pdf
from app.storage import minio_service
from app.config import settings
from pydantic import BaseModel
from datetime import datetime
import uuid
import httpx
import logging
import base64

logger = logging.getLogger(__name__)

class ReceiptRequest(BaseModel):
    title: str
    company_name: str
    company_cnpj: str
    employee_name: str
    employee_email: str
    employee_cpf: str
    amount: float
    reference_month: str
    description: str
    payment_date: str = None
    
    def __init__(self, **data):
        if data.get('payment_date') is None:
            data['payment_date'] = datetime.now().strftime("%d/%m/%Y")
        super().__init__(**data)

class SignatureResponse(BaseModel):
    id: str
    title: str
    status: str
    entity_type: str
    entity_id: int
    created_at: datetime
    signed_at: Optional[datetime] = None
    sign_url: Optional[str] = None
    provider_doc_id: Optional[str] = None
    signer_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class SignatureLinkResponse(BaseModel):
    sign_url: str
    signer_name: str
    signer_email: str
    status: str

router = APIRouter(prefix="/signatures", tags=["signatures"])


async def send_to_documenso(title: str, pdf_bytes: bytes, signers: list[dict]) -> dict:
    """
    Envia documento para Documenso e retorna info do documento criado com link de assinatura.
    
    Fluxo da API Documenso v1:
    1. POST /documents - Criar documento com PDF em base64
    2. POST /documents/{id}/recipients - Adicionar signatários
    3. POST /documents/{id}/send - Enviar para assinatura
    4. GET /documents/{id} - Obter detalhes incluindo signing URL
    """
    # Se não houver API key configurada, gerar link local simulado
    if not settings.DOCUMENSO_API_KEY or settings.DOCUMENSO_API_KEY == "your_api_key_here":
        logger.warning("Documenso API key not configured - generating local signature link")
        doc_id = str(uuid.uuid4())
        return {
            "id": doc_id,
            "status": "pending_local",
            "sign_url": None,
            "message": "Documenso não configurado - assinatura local pendente"
        }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.DOCUMENSO_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 1. Criar documento
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            logger.info(f"Creating document in Documenso: {title}")
            create_response = await client.post(
                f"{settings.DOCUMENSO_API_URL}/documents",
                headers=headers,
                json={
                    "title": title,
                    "documentDataId": pdf_base64,  # Documenso aceita base64 ou URL
                    "recipients": [
                        {
                            "email": signer["email"],
                            "name": signer["name"],
                            "role": "SIGNER"
                        }
                        for signer in signers
                    ],
                    "meta": {
                        "subject": f"Documento para assinatura: {title}",
                        "message": "Por favor, assine este documento.",
                        "timezone": "America/Sao_Paulo"
                    }
                }
            )
            
            if create_response.status_code not in [200, 201]:
                logger.error(f"Documenso create error: {create_response.status_code} - {create_response.text}")
                # Tentar formato alternativo
                create_response = await client.post(
                    f"{settings.DOCUMENSO_API_URL}/documents/create-document",
                    headers=headers,
                    json={
                        "title": title,
                        "document": pdf_base64,
                        "recipients": [{"email": s["email"], "name": s["name"]} for s in signers]
                    }
                )
                
                if create_response.status_code not in [200, 201]:
                    raise Exception(f"Failed to create document: {create_response.text}")
            
            doc_data = create_response.json()
            doc_id = doc_data.get("id") or doc_data.get("documentId")
            logger.info(f"Document created with ID: {doc_id}")
            
            # 2. Obter link de assinatura
            sign_url = None
            recipients = doc_data.get("recipients", [])
            
            if recipients:
                # O link pode vir direto na resposta
                for recipient in recipients:
                    if recipient.get("signingUrl"):
                        sign_url = recipient.get("signingUrl")
                        break
                    elif recipient.get("token"):
                        # Construir URL com token
                        sign_url = f"{settings.DOCUMENSO_API_URL.replace('/api/v1', '')}/sign/{recipient['token']}"
                        break
            
            # Se não veio na resposta, buscar detalhes do documento
            if not sign_url and doc_id:
                detail_response = await client.get(
                    f"{settings.DOCUMENSO_API_URL}/documents/{doc_id}",
                    headers=headers
                )
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    recipients = detail_data.get("recipients", detail_data.get("Recipient", []))
                    
                    for recipient in recipients:
                        token = recipient.get("token") or recipient.get("signingToken")
                        if token:
                            sign_url = f"https://app.documenso.com/sign/{token}"
                            break
            
            return {
                "id": str(doc_id),
                "status": "sent",
                "sign_url": sign_url,
                "message": "Document sent for signature"
            }
            
    except Exception as e:
        logger.error(f"Documenso error: {e}")
        return {
            "id": str(uuid.uuid4()),
            "status": "error",
            "sign_url": None,
            "message": str(e)
        }


@router.post("/receipt", response_model=SignatureResponse)
async def create_receipt_signature(
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera um recibo PDF e envia para assinatura"""
    
    # 1. Generate PDF
    pdf_bytes = generate_receipt_pdf(request.model_dump())
    
    # 2. Save to MinIO
    doc_uuid = uuid.uuid4()
    date_str = datetime.now().strftime("%Y/%m/%d")
    storage_key = f"docs/original/{current_user.tenant_id}/receipt/{date_str}/{doc_uuid}.pdf"
    
    minio_service.put_object(storage_key, pdf_bytes, "application/pdf")
    
    # 3. Create DB record
    db_doc = SignatureDocument(
        id=doc_uuid,
        tenant_id=current_user.tenant_id,
        title=request.title,
        status="draft",
        original_storage_key=storage_key,
        entity_type="receipt",
        entity_id=0,
        provider="documenso",
        created_by_user_id=current_user.id
    )
    db.add(db_doc)
    
    # 4. Create signer record
    signer = SignatureSigner(
        document_id=doc_uuid,
        name=request.employee_name,
        email=request.employee_email,
        role="SIGNER",
        status="pending"
    )
    db.add(signer)
    
    # 5. Send to Documenso
    signers = [{"name": request.employee_name, "email": request.employee_email, "role": "SIGNER"}]
    sign_url = None
    
    try:
        result = await send_to_documenso(request.title, pdf_bytes, signers)
        db_doc.provider_doc_id = result.get("id")
        db_doc.status = result.get("status", "sent")
        db_doc.sign_url = result.get("sign_url")
        db_doc.requested_at = datetime.now()
        sign_url = result.get("sign_url")
    except Exception as e:
        logger.error(f"Failed to send to Documenso: {e}")
        db_doc.status = "error"
    
    await db.commit()
    await db.refresh(db_doc)
    
    return SignatureResponse(
        id=str(db_doc.id),
        title=db_doc.title,
        status=db_doc.status,
        entity_type=db_doc.entity_type,
        entity_id=db_doc.entity_id,
        created_at=db_doc.created_at,
        signed_at=db_doc.signed_at,
        sign_url=sign_url
    )


@router.get("/{id}/signing-link", response_model=SignatureLinkResponse)
async def get_signing_link(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém o link de assinatura para um documento"""
    try:
        doc_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    query = select(SignatureDocument).where(
        SignatureDocument.id == doc_uuid,
        SignatureDocument.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Buscar signatário
    signer_query = select(SignatureSigner).where(
        SignatureSigner.document_id == doc_uuid
    ).limit(1)
    signer_result = await db.execute(signer_query)
    signer = signer_result.scalar_one_or_none()
    
    if not signer:
        raise HTTPException(status_code=404, detail="No signer found for document")
    
    # Se já temos o link salvo
    if doc.sign_url:
        return SignatureLinkResponse(
            sign_url=doc.sign_url,
            signer_name=signer.name,
            signer_email=signer.email,
            status=doc.status
        )
    
    # Se não temos link mas temos provider_doc_id, tentar buscar do Documenso
    if doc.provider_doc_id and settings.DOCUMENSO_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.DOCUMENSO_API_URL}/documents/{doc.provider_doc_id}",
                    headers={"Authorization": f"Bearer {settings.DOCUMENSO_API_KEY}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    recipients = data.get("recipients", data.get("Recipient", []))
                    
                    for recipient in recipients:
                        token = recipient.get("token") or recipient.get("signingToken")
                        if token:
                            sign_url = f"https://app.documenso.com/sign/{token}"
                            doc.sign_url = sign_url
                            await db.commit()
                            
                            return SignatureLinkResponse(
                                sign_url=sign_url,
                                signer_name=signer.name,
                                signer_email=signer.email,
                                status=doc.status
                            )
        except Exception as e:
            logger.error(f"Error fetching signing link from Documenso: {e}")
    
    # Sem link disponível - gerar link local para download do PDF
    download_url = minio_service.generate_presigned_get(doc.original_storage_key)
    
    return SignatureLinkResponse(
        sign_url=download_url,
        signer_name=signer.name,
        signer_email=signer.email,
        status=doc.status
    )


@router.get("", response_model=List[SignatureResponse])
async def list_signatures(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista documentos de assinatura do tenant"""
    from sqlalchemy.orm import selectinload
    
    query = select(SignatureDocument).where(
        SignatureDocument.tenant_id == current_user.tenant_id
    ).options(
        selectinload(SignatureDocument.signers)
    ).order_by(SignatureDocument.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    docs = result.scalars().all()
    
    return [
        SignatureResponse(
            id=str(doc.id),
            title=doc.title,
            status=doc.status,
            entity_type=doc.entity_type,
            entity_id=doc.entity_id,
            created_at=doc.created_at,
            signed_at=doc.signed_at,
            sign_url=doc.sign_url,
            provider_doc_id=doc.provider_doc_id,
            signer_name=doc.signers[0].name if doc.signers else None
        )
        for doc in docs
    ]


@router.get("/{id}", response_model=SignatureResponse)
async def get_signature(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca documento de assinatura por ID"""
    try:
        doc_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    query = select(SignatureDocument).where(
        SignatureDocument.id == doc_uuid,
        SignatureDocument.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return SignatureResponse(
        id=str(doc.id),
        title=doc.title,
        status=doc.status,
        entity_type=doc.entity_type,
        entity_id=doc.entity_id,
        created_at=doc.created_at,
        signed_at=doc.signed_at
    )


@router.get("/{id}/download")
async def download_signature_document(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera URL para download do documento"""
    try:
        doc_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    query = select(SignatureDocument).where(
        SignatureDocument.id == doc_uuid,
        SignatureDocument.tenant_id == current_user.tenant_id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Use signed document if available, otherwise original
    storage_key = doc.signed_storage_key or doc.original_storage_key
    
    if not storage_key:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    download_url = minio_service.generate_presigned_get(storage_key, expires_minutes=60)
    
    return {"download_url": download_url}


@router.delete("/bulk")
async def bulk_delete_signatures(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta todos os documentos de assinatura do tenant"""
    from sqlalchemy import delete
    
    # Deletar signers primeiro (cascade deve fazer automaticamente, mas garantindo)
    await db.execute(
        delete(SignatureSigner).where(
            SignatureSigner.document_id.in_(
                select(SignatureDocument.id).where(
                    SignatureDocument.tenant_id == current_user.tenant_id
                )
            )
        )
    )
    
    # Deletar documentos
    result = await db.execute(
        delete(SignatureDocument).where(
            SignatureDocument.tenant_id == current_user.tenant_id
        )
    )
    
    await db.commit()
    
    return {
        "message": "Documentos removidos com sucesso",
        "deleted_count": result.rowcount
    }


@router.post("")
async def create_signature_request(
    title: str = Form(...),
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    signers: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria solicitação de assinatura com upload de arquivo"""
    try:
        signers_list = json.loads(signers)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid signers JSON")
    
    file_content = await file.read()
    
    # Save to MinIO
    doc_uuid = uuid.uuid4()
    date_str = datetime.now().strftime("%Y/%m/%d")
    storage_key = f"docs/original/{current_user.tenant_id}/{entity_type}/{date_str}/{doc_uuid}.pdf"
    
    minio_service.put_object(storage_key, file_content, "application/pdf")
    
    # Create DB record
    db_doc = SignatureDocument(
        id=doc_uuid,
        tenant_id=current_user.tenant_id,
        title=title,
        status="draft",
        original_storage_key=storage_key,
        entity_type=entity_type,
        entity_id=entity_id,
        provider="documenso",
        created_by_user_id=current_user.id
    )
    db.add(db_doc)
    
    # Create signers
    for signer_data in signers_list:
        signer = SignatureSigner(
            document_id=doc_uuid,
            name=signer_data["name"],
            email=signer_data["email"],
            role=signer_data.get("role", "SIGNER"),
            status="pending"
        )
        db.add(signer)
    
    # Send to Documenso
    try:
        result = await send_to_documenso(title, file_content, signers_list)
        db_doc.provider_doc_id = result.get("id")
        db_doc.status = result.get("status", "sent")
        db_doc.requested_at = datetime.now()
    except Exception as e:
        logger.error(f"Failed to send to Documenso: {e}")
        db_doc.status = "error"
    
    await db.commit()
    await db.refresh(db_doc)
    
    return SignatureResponse(
        id=str(db_doc.id),
        title=db_doc.title,
        status=db_doc.status,
        entity_type=db_doc.entity_type,
        entity_id=db_doc.entity_id,
        created_at=db_doc.created_at,
        signed_at=db_doc.signed_at
    )


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Processa webhooks do Documenso"""
    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data", {})
    document_id = data.get("documentId")
    
    if not document_id:
        return {"status": "ignored", "reason": "no document id"}
    
    # Find document
    query = select(SignatureDocument).where(
        SignatureDocument.provider_doc_id == str(document_id)
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    
    if not doc:
        logger.warning(f"Document not found for webhook: {document_id}")
        return {"status": "ignored", "reason": "document not found"}
    
    # Update based on event
    if event_type == "DOCUMENT_COMPLETED":
        doc.status = "completed"
        doc.signed_at = datetime.now()
    elif event_type == "DOCUMENT_DECLINED":
        doc.status = "declined"
    elif event_type == "SIGNER_SIGNED":
        signer_id = data.get("recipientId")
        if signer_id:
            signer_query = select(SignatureSigner).where(
                SignatureSigner.provider_signer_id == str(signer_id)
            )
            signer_result = await db.execute(signer_query)
            signer = signer_result.scalar_one_or_none()
            if signer:
                signer.status = "signed"
                signer.signed_at = datetime.now()
    
    await db.commit()
    return {"status": "ok"}
