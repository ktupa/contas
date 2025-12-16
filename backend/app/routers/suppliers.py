from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, Supplier
from app.schemas import SupplierCreate, SupplierUpdate, SupplierResponse
from app.auth import get_current_active_user, require_role

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=List[SupplierResponse])
async def list_suppliers(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista fornecedores"""
    query = select(Supplier).where(Supplier.tenant_id == current_user.tenant_id)
    
    if active_only:
        query = query.where(Supplier.active == True)
    
    query = query.order_by(Supplier.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Criar novo fornecedor"""
    supplier = Supplier(
        **supplier_data.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    """Atualizar fornecedor"""
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == current_user.tenant_id
        )
    )
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for key, value in supplier_data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    
    await db.commit()
    await db.refresh(supplier)
    return supplier
