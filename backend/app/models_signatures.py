from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class SignatureDocument(Base):
    __tablename__ = "signature_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    provider = Column(String, default="documenso", nullable=False)
    provider_doc_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    status = Column(String, default="draft", nullable=False)
    
    requested_at = Column(DateTime, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    
    original_storage_key = Column(String, nullable=False)
    signed_storage_key = Column(String, nullable=True)
    audit_storage_key = Column(String, nullable=True)
    
    original_sha256 = Column(String, nullable=True)
    signed_sha256 = Column(String, nullable=True)
    original_size = Column(Integer, nullable=True)
    signed_size = Column(Integer, nullable=True)
    
    sign_url = Column(String, nullable=True)
    signed_view_url = Column(String, nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime, server_default=text("now()"), nullable=False)

    signers = relationship("SignatureSigner", back_populates="document", cascade="all, delete-orphan")
    events = relationship("SignatureEvent", back_populates="document")


class SignatureSigner(Base):
    __tablename__ = "signature_signers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("signature_documents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, default="signer", nullable=False)
    status = Column(String, default="pending", nullable=False)
    provider_signer_id = Column(String, nullable=True)
    sign_url = Column(String, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=text("now()"), nullable=False)

    document = relationship("SignatureDocument", back_populates="signers")


class SignatureEvent(Base):
    __tablename__ = "signature_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("signature_documents.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=text("now()"), nullable=False)

    document = relationship("SignatureDocument", back_populates="events")
