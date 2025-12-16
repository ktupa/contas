from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User, Competency, CompetencyItem, Employee, Rubric, Payment
from app.schemas import (
    CompetencyCreate, CompetencyUpdate, CompetencyResponse,
    CompetencyItemCreate, CompetencyItemResponse,
    CompetencySummary
)
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/competencies", tags=["competencies"])


def calculate_totals(items: List[CompetencyItem], rubrics_map: dict) -> dict:
    """Calcula totais da competência considerando proventos e descontos"""
    total_proventos = 0.0
    total_descontos = 0.0
    total_clt = 0.0
    total_beneficios = 0.0
    
    for item in items:
        rubric = rubrics_map.get(item.rubric_id)
        if rubric:
            valor = float(item.value)
            
            # Soma proventos ou descontos
            if rubric.type == "provento":
                total_proventos += valor
            else:  # desconto
                total_descontos += valor
            
            # Itens que entram na base CLT
            if rubric.entra_clt:
                if rubric.type == "provento":
                    total_clt += valor
                else:
                    total_clt -= valor
            
            # Benefícios (apenas proventos)
            if rubric.category == "beneficio" and rubric.type == "provento":
                total_beneficios += valor
    
    # Total geral = proventos - descontos
    total_geral = total_proventos - total_descontos
    
    return {
        "total_proventos": total_proventos,
        "total_descontos": total_descontos,
        "total_clt": total_clt,
        "total_beneficios": total_beneficios,
        "total_geral": total_geral
    }


@router.get("", response_model=List[CompetencyResponse])
async def list_competencies(
    employee_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista competências"""
    query = select(Competency).where(Competency.tenant_id == current_user.tenant_id).options(
        selectinload(Competency.items),
        selectinload(Competency.payments)
    )
    
    if employee_id:
        query = query.where(Competency.employee_id == employee_id)
    if year:
        query = query.where(Competency.year == year)
    if month:
        query = query.where(Competency.month == month)
    if status:
        query = query.where(Competency.status == status)
    
    query = query.order_by(Competency.year.desc(), Competency.month.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/employee/{employee_id}", response_model=CompetencyResponse)
async def get_competency_by_employee(
    employee_id: int,
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Busca competência por funcionário, ano e mês"""
    result = await db.execute(
        select(Competency)
        .options(
            selectinload(Competency.items),
            selectinload(Competency.payments)
        )
        .where(
            Competency.employee_id == employee_id,
            Competency.year == year,
            Competency.month == month,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    return competency


@router.get("/{competency_id}", response_model=CompetencyResponse)
async def get_competency(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Busca competência por ID"""
    result = await db.execute(
        select(Competency)
        .options(
            selectinload(Competency.items),
            selectinload(Competency.payments)
        )
        .where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    return competency


@router.post("", response_model=CompetencyResponse, status_code=status.HTTP_201_CREATED)
async def create_competency(
    competency_data: CompetencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Criar nova competência"""
    # Verificar se colaborador existe
    result = await db.execute(
        select(Employee).where(
            Employee.id == competency_data.employee_id,
            Employee.tenant_id == current_user.tenant_id,
            Employee.active == True
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found or inactive")
    
    # Verificar se competência já existe
    result = await db.execute(
        select(Competency).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.employee_id == competency_data.employee_id,
                Competency.year == competency_data.year,
                Competency.month == competency_data.month
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Competency already exists for this employee and month"
        )
    
    competency = Competency(
        **competency_data.model_dump(),
        tenant_id=current_user.tenant_id,
        totals_json={"total_clt": 0, "total_beneficios": 0, "total_geral": 0}
    )
    db.add(competency)
    await db.commit()
    
    # Recarregar com relacionamentos usando selectinload
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Competency)
        .options(selectinload(Competency.items), selectinload(Competency.payments))
        .where(Competency.id == competency.id)
    )
    competency = result.scalar_one()
    
    return competency


@router.post("/{competency_id}/clone-from-previous", response_model=CompetencyResponse)
async def clone_from_previous(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro", "rh"))
):
    """Clona itens da competência anterior"""
    # Buscar competência atual
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    if competency.status == "fechada":
        raise HTTPException(status_code=400, detail="Cannot modify closed competency")
    
    # Buscar competência anterior
    prev_month = competency.month - 1
    prev_year = competency.year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    result = await db.execute(
        select(Competency).where(
            and_(
                Competency.tenant_id == current_user.tenant_id,
                Competency.employee_id == competency.employee_id,
                Competency.year == prev_year,
                Competency.month == prev_month
            )
        )
    )
    prev_competency = result.scalar_one_or_none()
    
    if not prev_competency:
        raise HTTPException(status_code=404, detail="Previous competency not found")
    
    # Buscar itens recorrentes da competência anterior
    result = await db.execute(
        select(CompetencyItem, Rubric).join(Rubric).where(
            and_(
                CompetencyItem.competency_id == prev_competency.id,
                Rubric.recurring == True,
                Rubric.active == True
            )
        )
    )
    prev_items = result.all()
    
    # Clonar itens
    for prev_item, rubric in prev_items:
        new_item = CompetencyItem(
            tenant_id=current_user.tenant_id,
            competency_id=competency.id,
            rubric_id=prev_item.rubric_id,
            value=prev_item.value,
            notes=f"Clonado de {prev_month:02d}/{prev_year}"
        )
        db.add(new_item)
    
    await db.commit()
    await db.refresh(competency)
    
    # Recalcular totais
    await recalculate_totals(competency, db)
    
    return competency


async def recalculate_totals(competency: Competency, db: AsyncSession):
    """Recalcula totais da competência"""
    # Buscar todos os itens
    result = await db.execute(
        select(CompetencyItem, Rubric).join(Rubric).where(
            CompetencyItem.competency_id == competency.id
        )
    )
    items_with_rubrics = result.all()
    
    rubrics_map = {r.id: r for _, r in items_with_rubrics}
    items = [i for i, _ in items_with_rubrics]
    
    totals = calculate_totals(items, rubrics_map)
    competency.totals_json = totals
    await db.commit()


@router.post("/{competency_id}/close", response_model=CompetencyResponse)
async def close_competency(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Fechar competência (bloqueia edição)"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    if competency.status == "fechada":
        raise HTTPException(status_code=400, detail="Competency already closed")
    
    competency.status = "fechada"
    competency.closed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(competency)
    return competency


@router.post("/{competency_id}/reopen", response_model=CompetencyResponse)
async def reopen_competency(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Reabrir competência (somente admin)"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    competency.status = "aberta"
    competency.closed_at = None
    await db.commit()
    await db.refresh(competency)
    return competency


@router.delete("/{competency_id}")
async def delete_competency(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Deletar competência"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    await db.delete(competency)
    await db.commit()
    return {"message": "Competency deleted successfully"}


# --- Items Endpoints ---

@router.get("/{competency_id}/items", response_model=List[CompetencyItemResponse])
async def list_items(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista itens da competência"""
    # Verificar se competência existe e pertence ao tenant
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
        select(CompetencyItem).where(CompetencyItem.competency_id == competency_id)
    )
    return result.scalars().all()


@router.post("/{competency_id}/items", status_code=status.HTTP_201_CREATED)
async def create_item(
    competency_id: int,
    item_data: CompetencyItemCreate,
    auto_generate_payment: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro", "rh"))
):
    """Adicionar item à competência"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    if competency.status == "fechada":
        raise HTTPException(status_code=400, detail="Cannot modify closed competency")
    
    # Verificar se rubrica existe
    result = await db.execute(
        select(Rubric).where(
            Rubric.id == item_data.rubric_id,
            Rubric.tenant_id == current_user.tenant_id,
            Rubric.active == True
        )
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    item = CompetencyItem(
        **item_data.model_dump(),
        tenant_id=current_user.tenant_id,
        competency_id=competency_id
    )
    db.add(item)
    await db.commit()
    
    # Recalcular totais
    await recalculate_totals(competency, db)
    
    # REMOVIDO: Criação automática de pagamento de desconto
    # Descontos já estão calculados no líquido (total_geral)
    # Não devem gerar pagamentos separados pois causam duplicação
    
    await db.refresh(item)
    return {
        "item": item,
        "rubric": rubric
    }


@router.delete("/{competency_id}/items/{item_id}")
async def delete_item(
    competency_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro", "rh"))
):
    """Remover item da competência"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    if competency.status == "fechada":
        raise HTTPException(status_code=400, detail="Cannot modify closed competency")
    
    result = await db.execute(
        select(CompetencyItem).where(
            CompetencyItem.id == item_id,
            CompetencyItem.competency_id == competency_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    
    # Recalcular totais
    await recalculate_totals(competency, db)
    
    return {"message": "Item deleted successfully"}


@router.put("/{competency_id}/items/{item_id}", response_model=CompetencyItemResponse)
async def update_item(
    competency_id: int,
    item_id: int,
    item_data: CompetencyItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro", "rh"))
):
    """Atualizar item da competência"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    if competency.status == "fechada":
        raise HTTPException(status_code=400, detail="Cannot modify closed competency")
    
    result = await db.execute(
        select(CompetencyItem).where(
            CompetencyItem.id == item_id,
            CompetencyItem.competency_id == competency_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Verificar se rubrica existe
    result = await db.execute(
        select(Rubric).where(
            Rubric.id == item_data.rubric_id,
            Rubric.tenant_id == current_user.tenant_id,
            Rubric.active == True
        )
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    item.rubric_id = item_data.rubric_id
    item.value = item_data.value
    item.notes = item_data.notes
    
    await db.commit()
    
    # Recalcular totais
    await recalculate_totals(competency, db)
    
    await db.refresh(item)
    return item


# --- Payments Endpoints (linked to competency) ---

@router.get("/{competency_id}/payments")
async def list_competency_payments(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista pagamentos da competência"""
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


@router.post("/{competency_id}/payments", status_code=status.HTTP_201_CREATED)
async def create_competency_payment(
    competency_id: int,
    payment_body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Criar pagamento para competência"""
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
    
    # Parse date - SEMPRE remove timezone para compatibilidade com PostgreSQL
    from datetime import datetime as dt
    payment_dt = dt.utcnow()  # naive datetime
    payment_date = payment_body.get("date") or payment_body.get("payment_date")
    if payment_date:
        try:
            parsed = dt.fromisoformat(payment_date.replace('Z', '+00:00'))
            # Remove timezone info
            payment_dt = parsed.replace(tzinfo=None)
        except:
            try:
                payment_dt = dt.strptime(payment_date, "%Y-%m-%d")
            except:
                pass
    
    payment = Payment(
        tenant_id=current_user.tenant_id,
        competency_id=competency_id,
        date=payment_dt,
        amount=payment_body.get("amount", 0),
        kind=payment_body.get("kind", "salario"),
        method=payment_body.get("method", "pix"),
        status="pago",
        description=payment_body.get("description"),
        notes=payment_body.get("notes"),
        created_at=dt.utcnow()
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.delete("/{competency_id}/payments/{payment_id}")
async def delete_competency_payment(
    competency_id: int,
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Remover pagamento da competência"""
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
        select(Payment).where(
            Payment.id == payment_id,
            Payment.competency_id == competency_id
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    await db.delete(payment)
    await db.commit()
    
    return {"message": "Payment deleted successfully"}


@router.get("/{competency_id}/summary", response_model=CompetencySummary)
async def get_summary(
    competency_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resumo da competência (dashboard)"""
    result = await db.execute(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.tenant_id == current_user.tenant_id
        )
    )
    competency = result.scalar_one_or_none()
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")
    
    # Total previsto
    total_previsto = competency.totals_json.get("total_geral", 0) if competency.totals_json else 0
    
    # Total pago (excluindo descontos automáticos de rubrica)
    # Descontos por rubrica já estão no total_previsto (total_geral)
    # Aqui contamos apenas pagamentos efetivos (não kind='desconto')
    result = await db.execute(
        select(func.sum(Payment.amount)).where(
            and_(
                Payment.competency_id == competency_id,
                Payment.status == "pago",
                Payment.kind != "desconto"  # Exclui descontos automáticos
            )
        )
    )
    total_pago = result.scalar() or 0
    
    # Pendências
    result = await db.execute(
        select(func.count(Payment.id)).where(
            and_(
                Payment.competency_id == competency_id,
                Payment.status == "pendente"
            )
        )
    )
    total_pendente = result.scalar() or 0
    
    # Exceções
    result = await db.execute(
        select(func.count(Payment.id)).where(
            and_(
                Payment.competency_id == competency_id,
                Payment.exception_reason.isnot(None)
            )
        )
    )
    total_excecoes = result.scalar() or 0
    
    return CompetencySummary(
        total_previsto=float(total_previsto),
        total_pago=float(total_pago),
        saldo_a_pagar=float(total_previsto) - float(total_pago),
        total_pendente=total_pendente,
        total_excecoes=total_excecoes
    )
