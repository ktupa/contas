from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String, Integer, Boolean, DateTime, Numeric, Text, Index, UniqueConstraint, ForeignKey, JSON
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base
from app.models_signatures import SignatureDocument, SignatureSigner, SignatureEvent


class Tenant(Base):
    __tablename__ = "tenants"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    employees: Mapped[list["Employee"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # admin, financeiro, rh, leitura
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    
    __table_args__ = (
        Index("idx_users_tenant_email", "tenant_id", "email"),
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
    )


class Employee(Base):
    """Funcionário - associado a uma empresa"""
    __tablename__ = "employees"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"))  # Empresa onde trabalha
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200))  # Email do funcionário para assinaturas
    cpf: Mapped[Optional[str]] = mapped_column(String(14))  # CPF do funcionário
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)  # cargo
    regime: Mapped[str] = mapped_column(String(20), nullable=False)  # CLT, PJ
    base_salary: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))  # Salário base
    cost_center: Mapped[Optional[str]] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="employees")
    company: Mapped["Company"] = relationship(back_populates="employees", foreign_keys=[company_id])
    competencies: Mapped[list["Competency"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_employees_tenant", "tenant_id"),
        Index("idx_employees_company", "company_id"),
    )


class Rubric(Base):
    __tablename__ = "rubrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=True)  # código da rubrica
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="provento")  # provento, desconto
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # folha, beneficio, reembolso
    calculation_type: Mapped[str] = mapped_column(String(20), default="fixed")  # fixed, percentage
    default_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))  # valor padrão da rubrica
    entra_clt: Mapped[bool] = mapped_column(Boolean, default=True)
    entra_calculo_percentual: Mapped[bool] = mapped_column(Boolean, default=True)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_rubrics_tenant", "tenant_id"),
    )


class Competency(Base):
    __tablename__ = "competencies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="aberta")  # aberta, fechada
    base_percentual: Mapped[str] = mapped_column(String(20), default="CLT")  # CLT, TOTAL
    totals_json: Mapped[Optional[dict]] = mapped_column(JSON)  # {total_clt, total_beneficios, total_geral}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    employee: Mapped["Employee"] = relationship(back_populates="competencies")
    items: Mapped[list["CompetencyItem"]] = relationship(back_populates="competency", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="competency", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_competencies_tenant_employee", "tenant_id", "employee_id"),
        UniqueConstraint("tenant_id", "employee_id", "year", "month", name="uq_competency_employee_month"),
    )


class CompetencyItem(Base):
    __tablename__ = "competency_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    competency_id: Mapped[int] = mapped_column(Integer, ForeignKey("competencies.id"), nullable=False)
    rubric_id: Mapped[int] = mapped_column(Integer, ForeignKey("rubrics.id"), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    competency: Mapped["Competency"] = relationship(back_populates="items")
    rubric: Mapped["Rubric"] = relationship()
    
    __table_args__ = (
        Index("idx_competency_items_tenant_competency", "tenant_id", "competency_id"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    competency_id: Mapped[int] = mapped_column(Integer, ForeignKey("competencies.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # adiantamento, vale, salario, beneficio, outros, desconto
    method: Mapped[str] = mapped_column(String(50), nullable=False)  # pix, dinheiro, cartao
    status: Mapped[str] = mapped_column(String(50), default="pendente")  # pendente, pago, estornado
    description: Mapped[Optional[str]] = mapped_column(Text)  # Descrição do pagamento
    rubrica_name: Mapped[Optional[str]] = mapped_column(String(200))  # Nome da rubrica (para recibos)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    exception_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Campos de assinatura
    signature_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))  # UUID do documento de assinatura
    signature_status: Mapped[Optional[str]] = mapped_column(String(50))  # draft, sent, completed
    signature_url: Mapped[Optional[str]] = mapped_column(String(500))  # Link de assinatura
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Data de assinatura

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    competency: Mapped["Competency"] = relationship(back_populates="payments")

    __table_args__ = (
        Index("idx_payments_tenant_competency", "tenant_id", "competency_id"),
        Index("idx_payments_status", "status"),
    )


class Attachment(Base):
    __tablename__ = "attachments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # payment, competency, etc
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)  # chave no MinIO
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_attachments_entity", "tenant_id", "entity_type", "entity_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_refresh_tokens_expires", "expires_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    changes: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_audit_log_tenant_created", "tenant_id", "created_at"),
        Index("idx_audit_log_created", "created_at"),
    )


class Company(Base):
    """Empresa - conceito central do sistema de controle financeiro"""
    __tablename__ = "companies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20))
    ie: Mapped[Optional[str]] = mapped_column(String(20))  # Inscrição Estadual
    im: Mapped[Optional[str]] = mapped_column(String(20))  # Inscrição Municipal
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Endereço completo para NF-e
    cep: Mapped[Optional[str]] = mapped_column(String(10))
    logradouro: Mapped[Optional[str]] = mapped_column(String(200))
    numero: Mapped[Optional[str]] = mapped_column(String(20))
    complemento: Mapped[Optional[str]] = mapped_column(String(100))
    bairro: Mapped[Optional[str]] = mapped_column(String(100))
    cidade: Mapped[Optional[str]] = mapped_column(String(100))
    uf: Mapped[Optional[str]] = mapped_column(String(2))  # Sigla UF (SP, GO, etc)
    codigo_ibge_cidade: Mapped[Optional[str]] = mapped_column(String(10))  # Código IBGE da cidade
    codigo_ibge_uf: Mapped[Optional[str]] = mapped_column(String(2))  # Código IBGE da UF (35, 52, etc)
    
    # Campos legados (compatibilidade)
    address: Mapped[Optional[str]] = mapped_column(String(500))  # Campo antigo, manter para compatibilidade
    
    # Regime tributário
    regime_tributario: Mapped[Optional[str]] = mapped_column(String(20))  # simples, lucro_presumido, lucro_real
    
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)  # Empresa principal (própria)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    employees: Mapped[list["Employee"]] = relationship(back_populates="company", foreign_keys="Employee.company_id")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="company")
    
    __table_args__ = (
        Index("idx_companies_tenant", "tenant_id"),
    )


class Expense(Base):
    """Despesas - associadas a empresas e opcionalmente a funcionários"""
    __tablename__ = "expenses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"))  # Empresa responsável
    employee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("employees.id"))  # Funcionário associado (vale, adiantamento)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Data de vencimento
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # administrativo, operacional, impostos, vale, adiantamento, salario
    recurrence: Mapped[str] = mapped_column(String(20), default="pontual")  # pontual, mensal
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente, pago
    paid_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Data do pagamento
    notes: Mapped[Optional[str]] = mapped_column(Text)  # Observações
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company: Mapped["Company"] = relationship(back_populates="expenses")
    employee: Mapped["Employee"] = relationship(back_populates="expenses")
    
    __table_args__ = (
        Index("idx_expenses_tenant_date", "tenant_id", "date"),
        Index("idx_expenses_company", "company_id"),
        Index("idx_expenses_employee", "employee_id"),
    )


# ==================== MÓDULO FISCAL ====================

class CompanyCertificate(Base):
    """Certificado Digital A1 (.pfx) de uma empresa"""
    __tablename__ = "company_certificates"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa_text('gen_random_uuid()'))
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(20), nullable=False)
    cert_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)  # path no MinIO
    cert_password_enc: Mapped[str] = mapped_column(Text, nullable=False)  # senha criptografada AES-GCM
    cert_thumbprint: Mapped[Optional[str]] = mapped_column(String(200))  # hash/serial do certificado
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")  # active, inactive, expired, error
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    
    # Relationships
    company: Mapped["Company"] = relationship()
    
    __table_args__ = (
        Index("idx_company_certificates_company", "company_id"),
        Index("idx_company_certificates_status", "status"),
        UniqueConstraint("company_id", name="uq_company_certificate"),
    )


class SefazDfeState(Base):
    """Estado de sincronização DF-e por empresa"""
    __tablename__ = "sefaz_dfe_state"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa_text('gen_random_uuid()'))
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    last_nsu: Mapped[str] = mapped_column(String(20), nullable=False, server_default="0")  # NSU incremental
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ok")  # ok, error
    last_cstat: Mapped[Optional[str]] = mapped_column(String(10))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    company: Mapped["Company"] = relationship()
    
    __table_args__ = (
        Index("idx_sefaz_dfe_state_company", "company_id"),
        UniqueConstraint("company_id", name="uq_sefaz_state_company"),
    )


class NfeDocument(Base):
    """Documento NF-e importado da SEFAZ"""
    __tablename__ = "nfe_documents"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa_text('gen_random_uuid()'))
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    chave: Mapped[str] = mapped_column(String(44), nullable=False)  # chave de acesso 44 dígitos
    nsu: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # recebida, emitida, desconhecida
    situacao: Mapped[str] = mapped_column(String(20), nullable=False, server_default="desconhecida")  # autorizada, cancelada, denegada
    numero: Mapped[Optional[str]] = mapped_column(String(20))
    serie: Mapped[Optional[str]] = mapped_column(String(10))
    data_emissao: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cnpj_emitente: Mapped[Optional[str]] = mapped_column(String(20))
    emitente_nome: Mapped[Optional[str]] = mapped_column(String(200))
    cnpj_destinatario: Mapped[Optional[str]] = mapped_column(String(20))
    destinatario_nome: Mapped[Optional[str]] = mapped_column(String(200))
    valor_total: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    xml_kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="summary")  # summary, full
    xml_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)  # path no MinIO
    xml_sha256: Mapped[Optional[str]] = mapped_column(String(64))  # hash SHA-256 do XML
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    
    # Relationships
    company: Mapped["Company"] = relationship()
    
    __table_args__ = (
        Index("idx_nfe_documents_company", "company_id"),
        Index("idx_nfe_documents_chave", "chave"),
        Index("idx_nfe_documents_nsu", "nsu"),
        Index("idx_nfe_documents_tipo", "tipo"),
        Index("idx_nfe_documents_data_emissao", "data_emissao"),
        UniqueConstraint("chave", name="uq_nfe_chave"),
    )


class NfeSyncLog(Base):
    """Log de sincronizações NF-e (retenção 180 dias)"""
    __tablename__ = "nfe_sync_logs"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa_text('gen_random_uuid()'))
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)  # incremental, by_key, manual
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, error, partial
    docs_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa_text('0'))
    docs_imported: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa_text('0'))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    company: Mapped["Company"] = relationship()
    
    __table_args__ = (
        Index("idx_nfe_sync_logs_company", "company_id"),
        Index("idx_nfe_sync_logs_started_at", "started_at"),
    )


class NfeManifestation(Base):
    """Eventos de manifestação do destinatário"""
    __tablename__ = "nfe_manifestations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa_text('gen_random_uuid()'))
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    chave: Mapped[str] = mapped_column(String(44), nullable=False)
    tp_evento: Mapped[str] = mapped_column(String(10), nullable=False)
    dh_evento: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    protocolo: Mapped[Optional[str]] = mapped_column(String(100))
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa_text('0'))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=sa_text('now()'))

    __table_args__ = (
        UniqueConstraint("company_id", "chave", "tp_evento", name="uq_manifestation_company_chave_tp"),
        Index("idx_manifest_company", "company_id"),
        Index("idx_manifest_chave", "chave"),
        Index("idx_manifest_status", "status"),
    )

