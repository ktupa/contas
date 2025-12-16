from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, Attachment
from app.schemas import (
    AttachmentPresignRequest,
    AttachmentPresignResponse,
    AttachmentCommit,
    AttachmentResponse
)
from app.auth import get_current_active_user
from app.storage import minio_service

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("/presign", response_model=AttachmentPresignResponse)
async def presign_upload(
    request: AttachmentPresignRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Gera URL assinada para upload no MinIO"""
    upload_url, object_key = minio_service.generate_presigned_url(
        filename=request.filename,
        content_type=request.content_type,
        tenant_id=current_user.tenant_id
    )
    
    return AttachmentPresignResponse(
        upload_url=upload_url,
        object_key=object_key
    )


@router.post("/commit", response_model=AttachmentResponse)
async def commit_attachment(
    data: AttachmentCommit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Confirma upload e salva metadados no banco"""
    attachment = Attachment(
        tenant_id=current_user.tenant_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        key=data.object_key,
        size=data.size,
        sha256=data.sha256,
        mime=data.mime
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    
    # Gerar URL de download
    download_url = minio_service.generate_download_url(attachment.key)
    
    return AttachmentResponse(
        id=attachment.id,
        entity_type=attachment.entity_type,
        entity_id=attachment.entity_id,
        key=attachment.key,
        size=attachment.size,
        mime=attachment.mime,
        download_url=download_url,
        created_at=attachment.created_at
    )


@router.get("", response_model=List[AttachmentResponse])
async def list_attachments(
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista anexos de uma entidade"""
    result = await db.execute(
        select(Attachment).where(
            Attachment.tenant_id == current_user.tenant_id,
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id
        ).order_by(Attachment.created_at.desc())
    )
    attachments = result.scalars().all()
    
    # Gerar URLs de download
    response = []
    for attachment in attachments:
        download_url = minio_service.generate_download_url(attachment.key)
        response.append(
            AttachmentResponse(
                id=attachment.id,
                entity_type=attachment.entity_type,
                entity_id=attachment.entity_id,
                key=attachment.key,
                size=attachment.size,
                mime=attachment.mime,
                download_url=download_url,
                created_at=attachment.created_at
            )
        )
    
    return response


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deletar anexo"""
    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.tenant_id == current_user.tenant_id
        )
    )
    attachment = result.scalar_one_or_none()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Deletar do MinIO
    minio_service.delete_object(attachment.key)
    
    # Deletar do banco
    await db.delete(attachment)
    await db.commit()
    
    return {"message": "Attachment deleted successfully"}
