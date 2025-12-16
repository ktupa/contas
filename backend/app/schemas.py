from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_serializer, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Auth Schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = Field(..., pattern="^(admin|financeiro|rh|leitura)$")


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    tenant_id: int
    active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Employee Schemas
class EmployeeBase(BaseModel):
    name: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    role_name: str
    regime: str = Field(..., pattern="^(CLT|PJ)$")
    base_salary: Optional[float] = None
    cost_center: Optional[str] = None
    company_id: Optional[int] = None  # Empresa onde trabalha


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    role_name: Optional[str] = None
    regime: Optional[str] = None
    base_salary: Optional[float] = None
    cost_center: Optional[str] = None
    company_id: Optional[int] = None
    active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    id: int
    tenant_id: int
    active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Rubric Schemas
class RubricBase(BaseModel):
    code: Optional[str] = None
    name: str
    type: str = Field(default="provento", pattern="^(provento|desconto)$")
    category: str = Field(..., pattern="^(folha|beneficio|reembolso)$")
    calculation_type: str = Field(default="fixed", pattern="^(fixed|percentage)$")
    default_value: Optional[float] = None
    entra_clt: bool = True
    entra_calculo_percentual: bool = True
    recurring: bool = False


class RubricCreate(RubricBase):
    pass


class RubricUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    calculation_type: Optional[str] = None
    default_value: Optional[float] = None
    entra_clt: Optional[bool] = None
    entra_calculo_percentual: Optional[bool] = None
    recurring: Optional[bool] = None
    active: Optional[bool] = None


class RubricResponse(RubricBase):
    id: int
    tenant_id: int
    active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Payment Schemas
class PaymentBase(BaseModel):
    date: datetime
    amount: float
    kind: str = Field(..., pattern="^(adiantamento|vale|salario|beneficio|outros|desconto)$")
    method: str = Field(..., pattern="^(pix|dinheiro|cartao|transferencia)$")
    description: Optional[str] = None
    rubrica_name: Optional[str] = None
    notes: Optional[str] = None
    exception_reason: Optional[str] = None
    
    @field_validator('date', mode='before')
    @classmethod
    def strip_timezone(cls, v):
        """Remove timezone info to store as naive datetime (UTC assumed)"""
        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        if isinstance(v, str):
            from dateutil import parser
            dt = parser.parse(v)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        return v


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    date: Optional[datetime] = None
    amount: Optional[float] = None
    kind: Optional[str] = None
    method: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pendente|pago|estornado)$")
    description: Optional[str] = None
    rubrica_name: Optional[str] = None
    notes: Optional[str] = None
    exception_reason: Optional[str] = None


class PaymentResponse(PaymentBase):
    id: int
    tenant_id: int
    competency_id: int
    status: str
    created_at: datetime
    signature_id: Optional[UUID] = None
    signature_status: Optional[str] = None
    signature_url: Optional[str] = None
    signed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('signature_id')
    def serialize_signature_id(self, signature_id: Optional[UUID]) -> Optional[str]:
        return str(signature_id) if signature_id else None


# Competency Schemas
class CompetencyCreate(BaseModel):
    employee_id: int
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    base_percentual: str = Field(default="CLT", pattern="^(CLT|TOTAL)$")


class CompetencyUpdate(BaseModel):
    base_percentual: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(aberta|fechada)$")


class CompetencyItemBase(BaseModel):
    rubric_id: int
    value: float
    notes: Optional[str] = None


class CompetencyItemCreate(CompetencyItemBase):
    pass


class CompetencyItemResponse(CompetencyItemBase):
    id: int
    competency_id: int
    
    model_config = ConfigDict(from_attributes=True)


class CompetencyResponse(BaseModel):
    id: int
    tenant_id: int
    employee_id: int
    year: int
    month: int
    status: str
    base_percentual: str
    totals_json: Optional[dict] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    items: List[CompetencyItemResponse] = []
    payments: List[PaymentResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


# Attachment Schemas
class AttachmentPresignRequest(BaseModel):
    entity_type: str
    entity_id: int
    filename: str
    content_type: str


class AttachmentPresignResponse(BaseModel):
    upload_url: str
    object_key: str


class AttachmentCommit(BaseModel):
    entity_type: str
    entity_id: int
    object_key: str
    size: int
    sha256: str
    mime: str


class AttachmentResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    key: str
    size: int
    mime: str
    download_url: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Summary Schemas
class CompetencySummary(BaseModel):
    total_previsto: float
    total_pago: float
    saldo_a_pagar: float
    total_pendente: int
    total_excecoes: int


# Report Schemas
class MonthlyReport(BaseModel):
    employee_id: int
    employee_name: str
    total_clt: float
    total_beneficios: float
    total_geral: float
    total_pago: float
    pendencias: int
    excecoes: int


# Supplier Schemas
class SupplierBase(BaseModel):
    name: str
    cnpj: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Company Schemas (Empresa - conceito central)
class CompanyBase(BaseModel):
    name: str
    cnpj: Optional[str] = None
    ie: Optional[str] = None  # Inscrição Estadual
    im: Optional[str] = None  # Inscrição Municipal
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    
    # Endereço completo para NF-e
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None  # Sigla UF (SP, GO, etc)
    codigo_ibge_cidade: Optional[str] = None  # Código IBGE da cidade
    codigo_ibge_uf: Optional[str] = None  # Código IBGE da UF (35, 52, etc)
    
    # Campo legado (compatibilidade)
    address: Optional[str] = None
    
    # Regime tributário
    regime_tributario: Optional[str] = None  # simples, lucro_presumido, lucro_real
    
    is_main: bool = False  # Empresa principal (própria)
    active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    ie: Optional[str] = None
    im: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    codigo_ibge_cidade: Optional[str] = None
    codigo_ibge_uf: Optional[str] = None
    address: Optional[str] = None
    regime_tributario: Optional[str] = None
    is_main: Optional[bool] = None
    active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)



# Expense Schemas
class ExpenseBase(BaseModel):
    company_id: Optional[int] = None  # Empresa responsável pela despesa
    employee_id: Optional[int] = None  # Funcionário associado (vale, adiantamento)
    description: str
    amount: float
    date: datetime
    due_date: Optional[datetime] = None  # Data de vencimento
    category: str  # administrativo, operacional, impostos, vale, adiantamento, salario
    recurrence: str = Field(default="pontual", pattern="^(pontual|mensal)$")
    status: str = Field(default="pendente", pattern="^(pendente|pago)$")
    notes: Optional[str] = None
    
    @field_validator('date', 'due_date', mode='before')
    @classmethod
    def strip_timezone(cls, v):
        """Remove timezone info to store as naive datetime (UTC assumed)"""
        if v is None:
            return v
        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        if isinstance(v, str):
            from dateutil import parser
            dt = parser.parse(v)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        return v


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    company_id: Optional[int] = None
    employee_id: Optional[int] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None
    recurrence: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class EmployeeExpenseSummary(BaseModel):
    employee_id: int
    employee_name: str
    base_salary: float
    total_expenses: float  # Total de despesas associadas (vale, adiantamento)
    total_paid: float  # Total já pago
    balance: float  # Saldo a pagar (base_salary - total_paid)


class ExpenseResponse(ExpenseBase):
    id: int
    tenant_id: int
    created_at: datetime
    company: Optional[CompanyResponse] = None
    employee: Optional[EmployeeResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


# Company Financial Summary
class CompanyFinancialSummary(BaseModel):
    company_id: int
    company_name: str
    total_employees: int
    total_expenses: float
    total_pending: float
    total_paid: float

