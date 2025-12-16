"""
Router para Empresas - Conceito central do sistema financeiro

Empresas podem ser:
- A própria empresa (is_main=True) - controle de contas da empresa
- Fornecedores/Parceiros - empresas externas
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.database import get_db
from app.models import User, Company, Employee, Expense
from app.schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse, 
    CompanyFinancialSummary, EmployeeResponse
)
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    active_only: bool = True,
    is_main: Optional[bool] = Query(None, description="Filtrar por empresa principal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista empresas cadastradas"""
    query = select(Company).where(Company.tenant_id == current_user.tenant_id)
    
    if active_only:
        query = query.where(Company.active == True)
    
    if is_main is not None:
        query = query.where(Company.is_main == is_main)
    
    query = query.order_by(Company.is_main.desc(), Company.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/main", response_model=CompanyResponse)
async def get_main_company(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retorna a empresa principal (própria)"""
    result = await db.execute(
        select(Company).where(
            Company.tenant_id == current_user.tenant_id,
            Company.is_main == True
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Empresa principal não cadastrada")
    
    return company


@router.get("/summary", response_model=List[CompanyFinancialSummary])
async def get_companies_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resumo financeiro por empresa"""
    # Buscar empresas
    companies_result = await db.execute(
        select(Company).where(
            Company.tenant_id == current_user.tenant_id,
            Company.active == True
        )
    )
    companies = companies_result.scalars().all()
    
    summaries = []
    for company in companies:
        # Contar funcionários
        emp_count = await db.execute(
            select(func.count(Employee.id)).where(
                Employee.company_id == company.id,
                Employee.active == True
            )
        )
        total_employees = emp_count.scalar() or 0
        
        # Somar despesas - usando filtros separados
        total_expenses = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.company_id == company.id)
        )
        
        pending_expenses = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.company_id == company.id, Expense.status == 'pendente')
        )
        
        paid_expenses = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.company_id == company.id, Expense.status == 'pago')
        )
        
        summaries.append(CompanyFinancialSummary(
            company_id=company.id,
            company_name=company.name,
            total_employees=total_employees,
            total_expenses=float(total_expenses.scalar() or 0),
            total_pending=float(pending_expenses.scalar() or 0),
            total_paid=float(paid_expenses.scalar() or 0)
        ))
    
    return summaries


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Buscar empresa por ID"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == current_user.tenant_id
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return company


@router.get("/{company_id}/employees", response_model=List[EmployeeResponse])
async def get_company_employees(
    company_id: int,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista funcionários de uma empresa"""
    query = select(Employee).where(
        Employee.company_id == company_id,
        Employee.tenant_id == current_user.tenant_id
    )
    
    if active_only:
        query = query.where(Employee.active == True)
    
    query = query.order_by(Employee.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Criar nova empresa"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== CRIAR EMPRESA === User: {current_user.username}, Tenant: {current_user.tenant_id}")
    logger.info(f"Payload recebido: {company_data.model_dump()}")
    
    # Se is_main=True, verificar se já existe uma empresa principal
    if company_data.is_main:
        existing = await db.execute(
            select(Company).where(
                Company.tenant_id == current_user.tenant_id,
                Company.is_main == True
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail="Já existe uma empresa principal cadastrada"
            )
    
    company = Company(
        **company_data.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    logger.info(f"Empresa criada: ID={company.id}, Nome={company.name}")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Atualizar empresa"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == current_user.tenant_id
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    # Se alterando is_main para True, verificar se já existe outra
    if company_data.is_main and not company.is_main:
        existing = await db.execute(
            select(Company).where(
                Company.tenant_id == current_user.tenant_id,
                Company.is_main == True,
                Company.id != company_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail="Já existe uma empresa principal cadastrada"
            )
    
    for key, value in company_data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    
    await db.commit()
    await db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Excluir empresa (soft delete)"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == current_user.tenant_id
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    if company.is_main:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir a empresa principal"
        )
    
    # Verificar se há funcionários ou despesas vinculados
    emp_count = await db.execute(
        select(func.count(Employee.id)).where(Employee.company_id == company_id)
    )
    if emp_count.scalar() > 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir empresa com funcionários vinculados"
        )
    
    company.active = False
    await db.commit()
