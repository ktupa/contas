from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, RefreshToken
from app.schemas import UserLogin, Token, TokenRefresh, UserResponse
from app.auth import verify_password, create_access_token, create_refresh_token, get_current_active_user
from jose import jwt, JWTError
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login e geração de tokens"""
    result = await db.execute(
        select(User).where(User.email == credentials.email, User.active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Criar tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token_str, expires_at = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    # Salvar refresh token
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at
    )
    db.add(refresh_token)
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token_str
    )


@router.post("/refresh", response_model=Token)
async def refresh(
    token_request: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Renovar access token usando refresh token"""
    try:
        payload = jwt.decode(
            token_request.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verificar se token está válido
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_request.refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
    )
    stored_token = result.scalar_one_or_none()
    
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Buscar usuário
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Criar novos tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    )
    new_refresh_token_str, expires_at = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    # Revogar token antigo e criar novo
    stored_token.revoked = True
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token_str,
        expires_at=expires_at
    )
    db.add(new_refresh_token)
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token_str
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Retorna dados do usuário logado"""
    return current_user


@router.post("/logout")
async def logout(
    token_request: TokenRefresh,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Logout - revoga refresh token"""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_request.refresh_token,
            RefreshToken.user_id == current_user.id
        )
    )
    token = result.scalar_one_or_none()
    
    if token:
        token.revoked = True
        await db.commit()
    
    return {"message": "Logged out successfully"}
