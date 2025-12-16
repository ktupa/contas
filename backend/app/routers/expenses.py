from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models import User, Expense, Company, Employee
from app.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse, EmployeeExpenseSummary
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=List[ExpenseResponse])
async def list_expenses(
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    category: Optional[str] = None,
    expense_status: Optional[str] = Query(None, alias="status"),
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista despesas"""
    query = select(Expense).where(Expense.tenant_id == current_user.tenant_id)
    query = query.options(selectinload(Expense.company), selectinload(Expense.employee))
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            pass
            
    if category:
        query = query.where(Expense.category == category)
    if expense_status:
        query = query.where(Expense.status == expense_status)
    if employee_id:
        query = query.where(Expense.employee_id == employee_id)
        
    query = query.order_by(desc(Expense.date))

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Criar nova despesa"""
    # Verify company if provided
    if expense_data.company_id:
        result = await db.execute(
            select(Company).where(
                Company.id == expense_data.company_id,
                Company.tenant_id == current_user.tenant_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")
    
    # Verify employee if provided
    if expense_data.employee_id:
        result = await db.execute(
            select(Employee).where(
                Employee.id == expense_data.employee_id,
                Employee.tenant_id == current_user.tenant_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Employee not found")

    expense = Expense(
        **expense_data.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    
    # Reload with relationships
    result = await db.execute(
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.company), selectinload(Expense.employee))
    )
    return result.scalar_one()


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Atualizar despesa"""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == current_user.tenant_id
        ).options(selectinload(Expense.company), selectinload(Expense.employee))
    )
    expense = result.scalar_one_or_none()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Verify company if changing
    if expense_data.company_id is not None and expense_data.company_id != expense.company_id:
        company_result = await db.execute(
            select(Company).where(
                Company.id == expense_data.company_id,
                Company.tenant_id == current_user.tenant_id
            )
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")
    
    # Verify employee if changing
    if expense_data.employee_id is not None and expense_data.employee_id != expense.employee_id:
        employee_result = await db.execute(
            select(Employee).where(
                Employee.id == expense_data.employee_id,
                Employee.tenant_id == current_user.tenant_id
            )
        )
        if not employee_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Employee not found")

    for key, value in expense_data.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    
    await db.commit()
    await db.refresh(expense)
    return expense


@router.get("/employee-summary", response_model=List[EmployeeExpenseSummary])
async def get_employee_expense_summary(
    year: int = Query(..., description="Ano"),
    month: int = Query(..., ge=1, le=12, description="Mês"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resumo de despesas por funcionário (vales, adiantamentos) vs salário base"""
    # Buscar funcionários ativos
    emp_result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == current_user.tenant_id,
            Employee.active == True
        )
    )
    employees = emp_result.scalars().all()
    
    summaries = []
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    for emp in employees:
        # Buscar despesas do funcionário no mês (vales, adiantamentos)
        exp_result = await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.tenant_id == current_user.tenant_id,
                Expense.employee_id == emp.id,
                Expense.date >= start_date,
                Expense.date < end_date,
                Expense.category.in_(["vale", "adiantamento", "beneficio"])
            )
        )
        total_expenses = exp_result.scalar() or 0
        
        # Buscar despesas pagas
        paid_result = await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.tenant_id == current_user.tenant_id,
                Expense.employee_id == emp.id,
                Expense.date >= start_date,
                Expense.date < end_date,
                Expense.status == "pago"
            )
        )
        total_paid = paid_result.scalar() or 0
        
        # TODO: Buscar salário base da competência ou usar valor fixo
        # Por enquanto, usar um valor placeholder (idealmente viria da competência)
        base_salary = 0  # Será calculado com base nas rubricas
        
        summaries.append(EmployeeExpenseSummary(
            employee_id=emp.id,
            employee_name=emp.name,
            base_salary=base_salary,
            total_expenses=float(total_expenses),
            total_paid=float(total_paid),
            balance=base_salary - float(total_paid)
        ))
    
    return summaries


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Excluir despesa"""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == current_user.tenant_id
        )
    )
    expense = result.scalar_one_or_none()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await db.delete(expense)
    await db.commit()
