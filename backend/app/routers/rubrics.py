from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, Rubric
from app.schemas import RubricCreate, RubricUpdate, RubricResponse
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("", response_model=List[RubricResponse])
async def list_rubrics(
    active_only: bool = True,
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista rubricas"""
    query = select(Rubric).where(Rubric.tenant_id == current_user.tenant_id)
    
    if active_only:
        query = query.where(Rubric.active == True)
    
    if category:
        query = query.where(Rubric.category == category)
    
    query = query.order_by(Rubric.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=RubricResponse, status_code=status.HTTP_201_CREATED)
async def create_rubric(
    rubric_data: RubricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Criar nova rubrica"""
    rubric = Rubric(
        **rubric_data.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.put("/{rubric_id}", response_model=RubricResponse)
async def update_rubric(
    rubric_id: int,
    rubric_data: RubricUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Atualizar rubrica"""
    result = await db.execute(
        select(Rubric).where(
            Rubric.id == rubric_id,
            Rubric.tenant_id == current_user.tenant_id
        )
    )
    rubric = result.scalar_one_or_none()
    
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    for key, value in rubric_data.model_dump(exclude_unset=True).items():
        setattr(rubric, key, value)
    
    await db.commit()
    await db.refresh(rubric)
    return rubric
