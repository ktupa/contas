from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models import User, Payment, Competency, Employee, Company, Tenant
from app.schemas import PaymentCreate, PaymentUpdate, PaymentResponse
from app.auth import get_current_active_user, require_role
from app.services.pdf_generator import generate_receipt_pdf
from app.storage import minio_service
from app.models_signatures import SignatureDocument, SignatureSigner
from datetime import datetime
import uuid
import httpx
import base64
import logging
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


def check_adiantamento_limit(
    total_base: float,
    adiantamento_amount: float,
    limit_percent: float = 0.40
) -> tuple[bool, float]:
    """
    Verifica se adiantamento está dentro do limite
    Returns: (is_valid, percentage)
    """
    if total_base <= 0:
        return False, 0
    
    percentage = adiantamento_amount / total_base
    return percentage <= limit_percent, percentage


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista pagamentos de uma competência"""
    # Verificar competência
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    result = await db.execute(
        select(Payment).where(Payment.competency_id == competency_id)
        .order_by(Payment.date.desc())
    )
    return result.scalars().all()


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    competency_id: int,
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Criar novo pagamento"""
    # Verificar competência
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    # Verificar limite de adiantamento
    exception_reason = payment_data.exception_reason
    if payment_data.kind == "adiantamento":
        totals = competency.totals_json or {}
        
        # Determinar base de cálculo
        if competency.base_percentual == "CLT":
            base = totals.get("total_clt", 0)
        else:
            base = totals.get("total_geral", 0)
        
        # Buscar adiantamentos já pagos
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency_id,
                    Payment.kind == "adiantamento",
                    Payment.status != "estornado"
                )
            )
        )
        total_adiantamentos = result.scalar() or 0
        total_adiantamentos += payment_data.amount
        
        # Verificar limite
        is_valid_40, percentage = check_adiantamento_limit(base, total_adiantamentos, 0.40)
        is_valid_50, _ = check_adiantamento_limit(base, total_adiantamentos, 0.50)
        
        if not is_valid_40 and not is_valid_50:
            raise HTTPException(
                status_code=400,
                detail=f"Adiantamento excede 50% da base ({percentage*100:.1f}%). Não permitido."
            )
        
        if not is_valid_40 and is_valid_50:
            if not exception_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Adiantamento excede 40% ({percentage*100:.1f}%). Justificativa obrigatória."
                )
            exception_reason = f"Exceção: {percentage*100:.1f}% da base. {exception_reason}"
    
    # Prepara dados do payment - remove timezone de date se presente
    payment_dict = payment_data.model_dump()
    if payment_dict.get('date') and hasattr(payment_dict['date'], 'tzinfo') and payment_dict['date'].tzinfo:
        payment_dict['date'] = payment_dict['date'].replace(tzinfo=None)
    
    payment = Payment(
        **payment_dict,
        tenant_id=current_user.tenant_id,
        competency_id=competency_id,
        exception_reason=exception_reason,
        created_at=datetime.utcnow()  # naive datetime
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Atualizar pagamento"""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == current_user.tenant_id
        )
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    for key, value in payment_data.model_dump(exclude_unset=True).items():
        setattr(payment, key, value)
    
    await db.commit()
    await db.refresh(payment)
    return payment


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Deletar pagamento (somente admin)"""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == current_user.tenant_id
        )
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    await db.delete(payment)
    await db.commit()
    
    return {"message": "Payment deleted successfully"}


@router.post("/{payment_id}/generate-receipt")
async def generate_payment_receipt(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """
    Gera um recibo PDF para o pagamento e envia para assinatura do colaborador.
    """
    # Buscar pagamento com todas as relações necessárias
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == current_user.tenant_id
        )
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Buscar competência
    comp_result = await db.execute(
        select(Competency).where(Competency.id == payment.competency_id)
    )
    competency = comp_result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competência não encontrada")
    
    # Buscar colaborador
    emp_result = await db.execute(
        select(Employee).where(Employee.id == competency.employee_id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    
    if not employee.email:
        raise HTTPException(status_code=400, detail="Colaborador não possui e-mail cadastrado")
    
    # Buscar tenant (empresa)
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    # Buscar empresa do colaborador se existir
    company_name = tenant.name if tenant else "Empresa"
    company_cnpj = ""
    
    if employee.company_id:
        company_result = await db.execute(
            select(Company).where(Company.id == employee.company_id)
        )
        company = company_result.scalar_one_or_none()
        if company:
            company_name = company.name
            company_cnpj = company.cnpj or ""
    
    # Determinar tipo de pagamento
    kind_labels = {
        "vale": "Vale",
        "adiantamento": "Adiantamento",
        "salario": "Salário",
        "acerto": "Acerto",
        "bonus": "Bônus",
        "desconto": "Desconto"
    }
    payment_kind = kind_labels.get(payment.kind, payment.kind)
    
    # Montar título e descrição
    reference_month = f"{competency.month:02d}/{competency.year}"
    title = f"Recibo de {payment_kind} - {reference_month}"
    
    # Se tem rubrica_name, usar ela como descrição principal
    if payment.rubrica_name:
        description = payment.rubrica_name
    else:
        description = f"{payment_kind} referente à competência {reference_month}"
    
    if payment.notes:
        description += f"\nObservações: {payment.notes}"
    
    # Dados para o PDF
    receipt_data = {
        "title": title,
        "company_name": company_name,
        "company_cnpj": company_cnpj,
        "employee_name": employee.name,
        "employee_email": employee.email,
        "employee_cpf": employee.cpf or "",
        "amount": float(payment.amount),
        "reference_month": reference_month,
        "description": description,
        "rubrica_name": payment.rubrica_name,  # Adicionar rubrica_name
        "payment_date": payment.date.strftime("%d/%m/%Y") if payment.date else datetime.now().strftime("%d/%m/%Y")
    }
    
    # 1. Gerar PDF
    pdf_bytes = generate_receipt_pdf(receipt_data)
    
    # 2. Salvar no MinIO
    doc_uuid = uuid.uuid4()
    date_str = datetime.now().strftime("%Y/%m/%d")
    storage_key = f"docs/original/{current_user.tenant_id}/receipt/{date_str}/{doc_uuid}.pdf"
    
    minio_service.put_object(storage_key, pdf_bytes, "application/pdf")
    
    # 3. Criar registro no banco
    db_doc = SignatureDocument(
        id=doc_uuid,
        tenant_id=current_user.tenant_id,
        title=title,
        status="draft",
        original_storage_key=storage_key,
        entity_type="payment_receipt",
        entity_id=payment.id,
        provider="documenso",
        created_by_user_id=current_user.id
    )
    db.add(db_doc)
    
    # 4. Criar signer
    signer = SignatureSigner(
        document_id=doc_uuid,
        name=employee.name,
        email=employee.email,
        role="SIGNER",
        status="pending"
    )
    db.add(signer)
    
    # 5. Enviar para Documenso (se configurado)
    sign_url = None
    try:
        if settings.DOCUMENSO_API_KEY and settings.DOCUMENSO_API_KEY != "your_api_key_here":
            async with httpx.AsyncClient(timeout=60.0) as client:
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                headers = {
                    "Authorization": f"Bearer {settings.DOCUMENSO_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Passo 1: Criar documento e obter uploadUrl
                create_response = await client.post(
                    f"{settings.DOCUMENSO_API_URL}/documents",
                    headers=headers,
                    json={
                        "title": title,
                        "recipients": [{
                            "email": employee.email,
                            "name": employee.name,
                            "role": "SIGNER"
                        }],
                        "meta": {
                            "subject": f"Recibo para assinatura: {title}",
                            "message": "Por favor, assine este recibo de pagamento.",
                            "timezone": "America/Sao_Paulo",
                            "language": "pt-BR"
                        }
                    }
                )
                
                logger.info(f"Documenso create response: {create_response.status_code}")
                
                if create_response.status_code in [200, 201]:
                    doc_data = create_response.json()
                    doc_id = doc_data.get("documentId") or doc_data.get("id")
                    upload_url = doc_data.get("uploadUrl")
                    
                    db_doc.provider_doc_id = str(doc_id)
                    logger.info(f"Documento criado no Documenso. ID: {doc_id}")
                    
                    # Passo 2: Fazer upload do PDF
                    if upload_url:
                        upload_response = await client.put(
                            upload_url,
                            content=pdf_bytes,
                            headers={"Content-Type": "application/pdf"}
                        )
                        logger.info(f"Upload response: {upload_response.status_code}")
                    
                    # Passo 3: Adicionar campo de assinatura
                    recipients = doc_data.get("recipients", [])
                    if recipients:
                        recipient_id = recipients[0].get("recipientId")
                        if recipient_id:
                            field_response = await client.post(
                                f"{settings.DOCUMENSO_API_URL}/documents/{doc_id}/fields",
                                headers=headers,
                                json={
                                    "recipientId": recipient_id,
                                    "type": "SIGNATURE",
                                    "pageNumber": 1,
                                    "pageX": 100,
                                    "pageY": 650,
                                    "pageWidth": 200,
                                    "pageHeight": 60
                                }
                            )
                            logger.info(f"Field response: {field_response.status_code}")
                    
                    # Passo 4: Enviar documento para assinatura
                    send_response = await client.post(
                        f"{settings.DOCUMENSO_API_URL}/documents/{doc_id}/send",
                        headers=headers,
                        json={"sendEmail": True}
                    )
                    logger.info(f"Send response: {send_response.status_code}")
                    
                    if send_response.status_code in [200, 201]:
                        db_doc.status = "sent"
                        db_doc.requested_at = datetime.now()
                        
                        # Buscar documento atualizado para obter signing URLs
                        get_doc_response = await client.get(
                            f"{settings.DOCUMENSO_API_URL}/documents/{doc_id}",
                            headers=headers
                        )
                        
                        if get_doc_response.status_code == 200:
                            doc_updated = get_doc_response.json()
                            updated_recipients = doc_updated.get("recipients", [])
                            
                            logger.info(f"Documento atualizado retornou {len(updated_recipients)} recipients")
                            
                            # Obter signing URL do primeiro recipient
                            for recipient in updated_recipients:
                                signing_url = recipient.get("signingUrl") or recipient.get("signing_url")
                                token = recipient.get("token")
                                
                                logger.info(f"Recipient: email={recipient.get('email')}, token={token}, signingUrl={signing_url}")
                                
                                if signing_url:
                                    sign_url = signing_url
                                    db_doc.sign_url = sign_url
                                    logger.info(f"✅ Sign URL obtido: {sign_url}")
                                    break
                                elif token:
                                    # Construir URL a partir do token
                                    sign_url = f"https://app.documenso.com/sign/{token}"
                                    db_doc.sign_url = sign_url
                                    logger.info(f"✅ Sign URL construído do token: {sign_url}")
                                    break
                            
                            if not sign_url:
                                logger.warning(f"⚠️ Nenhum signing URL encontrado nos recipients: {updated_recipients}")
                        else:
                            logger.warning(f"Erro ao buscar documento atualizado: {get_doc_response.status_code}")
                    else:
                        logger.warning(f"Erro ao enviar documento: {send_response.text}")
                        db_doc.status = "draft"
                else:
                    error_text = create_response.text
                    error_msg = "Erro ao criar documento no Documenso"
                    
                    try:
                        error_data = create_response.json()
                        if "maximum number of documents" in error_data.get("message", "").lower():
                            error_msg = "Limite de documentos do Documenso atingido este mês"
                            logger.error(f"❌ DOCUMENSO QUOTA LIMIT: {error_data.get('message')}")
                        else:
                            error_msg = error_data.get("message", error_msg)
                    except:
                        pass
                    
                    logger.warning(f"Documenso response: {create_response.status_code} - {error_text}")
                    db_doc.status = "pending_local"
                    db_doc.error_message = error_msg
        else:
            # Sem Documenso, apenas marcar como pendente local
            db_doc.status = "pending_local"
            logger.info("Documenso não configurado - recibo salvo localmente")
            
    except Exception as e:
        logger.error(f"Erro ao enviar para Documenso: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db_doc.status = "pending_local"
    
    await db.commit()
    await db.refresh(db_doc)
    
    # Atualizar payment com dados de assinatura
    payment.signature_id = db_doc.id
    payment.signature_status = db_doc.status
    payment.signature_url = sign_url
    await db.commit()
    await db.refresh(payment)
    
    logger.info(f"✅ Payment atualizado: signature_id={payment.signature_id}, signature_url={payment.signature_url}")
    
    # Gerar URL de download do PDF
    download_url = minio_service.generate_presigned_get(storage_key, expires_minutes=60)
    
    response_data = {
        "message": "Recibo gerado com sucesso",
        "signature_id": str(db_doc.id),
        "status": db_doc.status,
        "download_url": download_url,
        "sign_url": sign_url,
        "employee_email": employee.email
    }
    
    # Adicionar mensagem de erro se houver
    if db_doc.status == "pending_local" and hasattr(db_doc, 'error_message') and db_doc.error_message:
        response_data["error_message"] = db_doc.error_message
    
    return response_data
