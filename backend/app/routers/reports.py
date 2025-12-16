from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List
from datetime import datetime
import pandas as pd
from io import BytesIO
from app.database import get_db
from app.models import User, Competency, Employee, Payment, CompetencyItem, Rubric
from app.schemas import MonthlyReport
from app.auth import get_current_active_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/competency/{month}/{year}")
async def competency_report_by_month_year(
    month: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Relatório por competência (formato: /month/year)"""
    # Buscar competências
    result = await db.execute(
        select(Competency, Employee).join(Employee).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.year == year,
                Competency.month == month
            )
        )
    )
    competencies_with_employees = result.all()
    
    if not competencies_with_employees:
        return {
            "month": month,
            "year": year,
            "total_earnings": 0,
            "total_deductions": 0,
            "net_total": 0,
            "payments": []
        }
    
    total_earnings = 0.0
    total_deductions = 0.0
    payments = []
    
    for competency, employee in competencies_with_employees:
        totals = competency.totals_json or {}
        
        proventos = totals.get("total_proventos", totals.get("total_geral", 0))
        descontos = totals.get("total_descontos", 0)
        liquido = totals.get("total_geral", 0)
        
        total_earnings += proventos
        total_deductions += descontos
        
        # Total pago
        pay_result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pago"
                )
            )
        )
        pago = pay_result.scalar() or 0
        
        payments.append({
            "id": competency.id,
            "employee_name": employee.name,
            "total_earnings": proventos,
            "total_deductions": descontos,
            "net_amount": liquido,
            "total_paid": float(pago),
            "status": "paid" if float(pago) >= liquido else "pending"
        })
    
    return {
        "month": month,
        "year": year,
        "total_earnings": total_earnings,
        "total_deductions": total_deductions,
        "net_total": total_earnings - total_deductions,
        "payments": payments
    }


@router.get("/competency/{competency_ref}")
async def competency_report(
    competency_ref: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Relatório por competência (formato: MM/YYYY ou MM-YYYY)"""
    # Parse do formato MM/YYYY ou MM-YYYY ou MM-YYYY
    try:
        if "/" in competency_ref:
            month, year = competency_ref.split("/")
        else:
            month, year = competency_ref.split("-")
        month = int(month)
        year = int(year)
    except:
        raise HTTPException(status_code=400, detail="Formato inválido. Use MM/YYYY")
    
    # Buscar competências
    result = await db.execute(
        select(Competency, Employee).join(Employee).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.year == year,
                Competency.month == month
            )
        )
    )
    competencies_with_employees = result.all()
    
    if not competencies_with_employees:
        raise HTTPException(status_code=404, detail="Nenhuma competência encontrada")
    
    total_earnings = 0.0
    total_deductions = 0.0
    payments = []
    
    for competency, employee in competencies_with_employees:
        totals = competency.totals_json or {}
        
        proventos = totals.get("total_proventos", totals.get("total_geral", 0))
        descontos = totals.get("total_descontos", 0)
        liquido = totals.get("total_geral", 0)
        
        total_earnings += proventos
        total_deductions += descontos
        
        # Total pago
        pay_result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pago"
                )
            )
        )
        pago = pay_result.scalar() or 0
        
        payments.append({
            "id": competency.id,
            "employee_name": employee.name,
            "total_earnings": proventos,
            "total_deductions": descontos,
            "net_amount": liquido,
            "total_paid": float(pago),
            "status": "paid" if float(pago) >= liquido else "pending"
        })
    
    return {
        "month": month,
        "year": year,
        "total_earnings": total_earnings,
        "total_deductions": total_deductions,
        "net_total": total_earnings - total_deductions,
        "payments": payments
    }


@router.get("/period")
async def period_report(
    start_date: str,
    end_date: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Relatório por período (YYYY-MM-DD)"""
    from datetime import datetime
    
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    
    # Buscar pagamentos no período
    result = await db.execute(
        select(Payment, Competency, Employee).join(
            Competency, Payment.competency_id == Competency.id
        ).join(
            Employee, Competency.employee_id == Employee.id
        ).where(
            and_(
                Payment.tenant_id == current_user.tenant_id,
                Payment.date >= start,
                Payment.date <= end
            )
        ).order_by(Payment.date.desc())
    )
    
    payments_data = result.all()
    
    total_paid = 0.0
    payments_list = []
    
    for payment, competency, employee in payments_data:
        total_paid += float(payment.amount)
        payments_list.append({
            "id": payment.id,
            "date": payment.date.isoformat(),
            "employee_name": employee.name,
            "competency": f"{competency.month:02d}/{competency.year}",
            "amount": float(payment.amount),
            "kind": payment.kind,
            "method": payment.method,
            "status": payment.status,
            "description": payment.description or payment.notes
        })
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_paid": total_paid,
        "payments_count": len(payments_list),
        "payments": payments_list
    }


@router.get("/monthly", response_model=List[MonthlyReport])
async def monthly_report(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Relatório mensal consolidado"""
    # Buscar competências do mês
    result = await db.execute(
        select(Competency, Employee).join(Employee).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.year == year,
                Competency.month == month
            )
        )
    )
    competencies_with_employees = result.all()
    
    reports = []
    for competency, employee in competencies_with_employees:
        totals = competency.totals_json or {}
        
        # Total pago
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pago"
                )
            )
        )
        total_pago = result.scalar() or 0
        
        # Pendências
        result = await db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pendente"
                )
            )
        )
        pendencias = result.scalar() or 0
        
        # Exceções
        result = await db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.exception_reason.isnot(None)
                )
            )
        )
        excecoes = result.scalar() or 0
        
        reports.append(
            MonthlyReport(
                employee_id=employee.id,
                employee_name=employee.name,
                total_clt=totals.get("total_clt", 0),
                total_beneficios=totals.get("total_beneficios", 0),
                total_geral=totals.get("total_geral", 0),
                total_pago=float(total_pago),
                pendencias=pendencias,
                excecoes=excecoes
            )
        )
    
    return reports


@router.get("/monthly.xlsx")
async def monthly_report_excel(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Exportar relatório mensal em Excel"""
    # Buscar dados
    result = await db.execute(
        select(Competency, Employee).join(Employee).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.year == year,
                Competency.month == month
            )
        )
    )
    competencies_with_employees = result.all()
    
    data = []
    for competency, employee in competencies_with_employees:
        totals = competency.totals_json or {}
        
        # Total pago
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pago"
                )
            )
        )
        total_pago = result.scalar() or 0
        
        data.append({
            "Colaborador": employee.name,
            "Cargo": employee.role_name,
            "Regime": employee.regime,
            "Total CLT": totals.get("total_clt", 0),
            "Total Benefícios": totals.get("total_beneficios", 0),
            "Total Geral": totals.get("total_geral", 0),
            "Total Pago": float(total_pago),
            "Saldo": totals.get("total_geral", 0) - float(total_pago),
            "Status": competency.status
        })
    
    # Criar Excel
    df = pd.DataFrame(data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=f"{month:02d}-{year}")
    
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{month:02d}_{year}.xlsx"
        }
    )


@router.get("/monthly.csv")
async def monthly_report_csv(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Exportar relatório mensal em CSV"""
    # Buscar dados
    result = await db.execute(
        select(Competency, Employee).join(Employee).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.year == year,
                Competency.month == month
            )
        )
    )
    competencies_with_employees = result.all()
    
    data = []
    for competency, employee in competencies_with_employees:
        totals = competency.totals_json or {}
        
        # Total pago
        result = await db.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.competency_id == competency.id,
                    Payment.status == "pago"
                )
            )
        )
        total_pago = result.scalar() or 0
        
        data.append({
            "Colaborador": employee.name,
            "Cargo": employee.role_name,
            "Regime": employee.regime,
            "Total CLT": totals.get("total_clt", 0),
            "Total Benefícios": totals.get("total_beneficios", 0),
            "Total Geral": totals.get("total_geral", 0),
            "Total Pago": float(total_pago),
            "Saldo": totals.get("total_geral", 0) - float(total_pago),
            "Status": competency.status
        })
    
    # Criar CSV
    df = pd.DataFrame(data)
    csv_content = df.to_csv(index=False)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{month:02d}_{year}.csv"
        }
    )
