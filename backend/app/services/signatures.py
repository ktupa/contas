from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import logging
from app.models_signatures import SignatureDocument, SignatureSigner, SignatureEvent
from app.services.documenso import DocumensoClient
from app.storage import minio_service
from app.config import settings

logger = logging.getLogger(__name__)

class SignaturesService:
    def __init__(self, db: Session):
        self.db = db
        self.documenso = DocumensoClient()

    async def create_signature_request(
        self,
        tenant_id: int,
        title: str,
        pdf_bytes: bytes,
        signers: list[dict], # [{name, email, role}]
        entity_type: str,
        entity_id: int,
        user_id: int = None
    ):
        # 1. Save Original to MinIO
        doc_uuid = uuid.uuid4()
        date_str = datetime.now().strftime("%Y/%m/%d")
        original_key = f"docs/original/{tenant_id}/{entity_type}/{date_str}/{doc_uuid}.pdf"
        
        minio_service.put_object(original_key, pdf_bytes, "application/pdf")

        # 2. Create DB Record
        db_doc = SignatureDocument(
            id=doc_uuid,
            tenant_id=tenant_id,
            title=title,
            status="draft",
            original_storage_key=original_key,
            entity_type=entity_type,
            entity_id=entity_id,
            provider="documenso",
            created_by_user_id=user_id
        )
        self.db.add(db_doc)
        self.db.commit()
        self.db.refresh(db_doc)

        try:
            # 3. Create in Documenso
            doc_response = await self.documenso.create_document(
                title=title,
                external_id=str(db_doc.id),
                pdf_bytes=pdf_bytes
            )
            provider_doc_id = doc_response.get("id")
            
            db_doc.provider_doc_id = str(provider_doc_id)
            
            # 4. Add Signers
            for signer_data in signers:
                recipient = await self.documenso.add_recipient(
                    document_id=provider_doc_id,
                    email=signer_data["email"],
                    name=signer_data["name"],
                    role=signer_data.get("role", "SIGNER")
                )
                
                # Create Signer in DB
                db_signer = SignatureSigner(
                    document_id=db_doc.id,
                    name=signer_data["name"],
                    email=signer_data["email"],
                    role=signer_data.get("role", "SIGNER"),
                    provider_signer_id=str(recipient.get("id")),
                    status="pending"
                )
                self.db.add(db_signer)
                
                # Add default field (Signature)
                # Assuming 1 page, bottom of page
                await self.documenso.add_field(
                    document_id=provider_doc_id,
                    recipient_id=recipient.get("id"),
                    type="SIGNATURE",
                    page=1,
                    x=10,
                    y=90,
                    width=20,
                    height=5
                )

            # 5. Send Document
            await self.documenso.send_document(provider_doc_id)
            
            db_doc.status = "sent"
            db_doc.requested_at = datetime.now()
            self.db.commit()
            
            return db_doc

        except Exception as e:
            logger.error(f"Error creating signature request: {e}")
            db_doc.status = "error"
            self.db.commit()
            raise e

    async def handle_webhook(self, payload: dict):
        """
        Processa webhooks do Documenso.
        """
        event_type = payload.get("type")
        data = payload.get("data", {})
        document_id = data.get("documentId")
        
        if not document_id:
            return

        # Find document by provider_doc_id
        doc = self.db.query(SignatureDocument).filter(
            SignatureDocument.provider_doc_id == str(document_id)
        ).first()
        
        if not doc:
            logger.warning(f"Document not found for webhook: {document_id}")
            return

        # Log event
        event = SignatureEvent(
            document_id=doc.id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)

        # Update status based on event
        if event_type == "DOCUMENT_COMPLETED":
            doc.status = "completed"
            doc.signed_at = datetime.now()
            
            # Download signed PDF and save to MinIO
            # Assuming Documenso provides a download URL or we fetch it
            # For now, we might need to fetch it via API if URL is not in payload
            try:
                # Fetch document details to get download URL or just download it
                # If Documenso API has a download endpoint, we use that.
                # Since we don't have a download method in client yet, let's add one or assume we can get it.
                # Usually GET /documents/{id} returns downloadUrl or similar.
                
                # For now, let's just mark as completed. 
                # Downloading requires implementing download in client.
                pass
            except Exception as e:
                logger.error(f"Error downloading signed document: {e}")

        elif event_type == "DOCUMENT_DECLINED":
            doc.status = "declined"
            doc.declined_at = datetime.now()
        
        elif event_type == "SIGNER_SIGNED":
            signer_id = data.get("recipientId")
            signer = self.db.query(SignatureSigner).filter(
                SignatureSigner.provider_signer_id == str(signer_id)
            ).first()
            if signer:
                signer.status = "signed"
                signer.signed_at = datetime.now()

        self.db.commit()
