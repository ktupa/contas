"""
Schemas Pydantic para o módulo fiscal (certificados e NF-e)
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from uuid import UUID


# ==================== CERTIFICADOS ====================

class CertificateUpload(BaseModel):
    """Schema para upload de certificado A1"""
    password: str = Field(..., description="Senha do certificado .pfx")


class CertificateResponse(BaseModel):
    """Schema de resposta do certificado"""
    id: UUID
    company_id: int
    cnpj: str
    cert_thumbprint: Optional[str]
    valid_from: datetime
    valid_to: datetime
    status: str
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CertificateUpdate(BaseModel):
    """Schema para atualização do certificado"""
    status: Optional[str] = Field(None, description="active, inactive, expired, error")


# ==================== NF-e DOCUMENTS ====================

class NfeDocumentBase(BaseModel):
    """Base schema para documento NF-e"""
    chave: str = Field(..., min_length=44, max_length=44, description="Chave de acesso da NF-e (44 dígitos)")
    nsu: str
    tipo: str = Field(..., description="recebida, emitida, desconhecida")
    situacao: str = Field(default="desconhecida", description="autorizada, cancelada, denegada, desconhecida")
    numero: Optional[str] = None
    serie: Optional[str] = None
    data_emissao: Optional[datetime] = None
    cnpj_emitente: Optional[str] = None
    emitente_nome: Optional[str] = None
    cnpj_destinatario: Optional[str] = None
    destinatario_nome: Optional[str] = None
    valor_total: Optional[float] = None
    xml_kind: Optional[str] = Field(default="summary", description="summary ou full")


class NfeDocumentCreate(NfeDocumentBase):
    """Schema para criação de documento NF-e"""
    company_id: int
    xml_storage_key: str
    xml_sha256: Optional[str] = None


class NfeDocumentResponse(NfeDocumentBase):
    """Schema de resposta do documento NF-e"""
    id: UUID
    company_id: int
    xml_storage_key: str
    xml_sha256: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NfeDocumentFilter(BaseModel):
    """Schema para filtros de busca de NF-e"""
    company_id: Optional[int] = None
    tipo: Optional[str] = None
    data_ini: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    emitente: Optional[str] = None
    valor_min: Optional[float] = None
    valor_max: Optional[float] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


class ImportByKeyRequest(BaseModel):
    """Schema para importação por chave de acesso"""
    company_id: int
    chave: str = Field(..., min_length=44, max_length=44, description="Chave de acesso da NF-e")


# ==================== SYNC STATE ====================

class SefazDfeStateResponse(BaseModel):
    """Schema de resposta do estado de sincronização"""
    id: UUID
    company_id: int
    last_nsu: str
    last_sync_at: Optional[datetime]
    last_status: str
    last_error: Optional[str]
    
    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    """Schema para requisição de sincronização"""
    company_id: Optional[int] = Field(None, description="ID da empresa (None = todas)")


class SyncResponse(BaseModel):
    """Schema de resposta de sincronização"""
    company_id: int
    status: str
    docs_found: int
    docs_imported: int
    last_nsu: str
    error_message: Optional[str] = None


# ==================== SYNC LOGS ====================

class NfeSyncLogResponse(BaseModel):
    """Schema de resposta de log de sincronização"""
    id: UUID
    company_id: int
    sync_type: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    docs_found: int
    docs_imported: int
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class NfeSyncLogFilter(BaseModel):
    """Schema para filtros de logs de sincronização"""
    company_id: Optional[int] = None
    sync_type: Optional[str] = None
    status: Optional[str] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


# ==================== MANIFESTAÇÃO ====================

class NfeManifestationResponse(BaseModel):
    id: UUID
    company_id: int
    chave: str
    tp_evento: str
    dh_evento: Optional[datetime]
    status: str
    protocolo: Optional[str]
    tentativas: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResolveResponse(BaseModel):
    company_id: int
    attempted: int
    resolved: int
    still_summary: int
    errors: Optional[str] = None
