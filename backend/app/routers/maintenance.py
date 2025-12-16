from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, RefreshToken, AuditLog
from app.auth import require_role
from app.config import settings
import structlog

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
logger = structlog.get_logger()


@router.post("/cleanup")
async def cleanup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """
    Limpeza de dados antigos (somente admin)
    - Remove sessões expiradas
    - Remove logs de auditoria antigos
    """
    results = {}
    
    # 1. Limpar refresh tokens expirados ou revogados antigos
    cutoff_date = datetime.utcnow() - timedelta(days=settings.SESSION_RETENTION_DAYS)
    
    result = await db.execute(
        delete(RefreshToken).where(
            (RefreshToken.expires_at < datetime.utcnow()) |
            ((RefreshToken.revoked == True) & (RefreshToken.created_at < cutoff_date))
        )
    )
    results["refresh_tokens_deleted"] = result.rowcount
    
    # 2. Limpar logs de auditoria antigos
    audit_cutoff = datetime.utcnow() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
    
    result = await db.execute(
        delete(AuditLog).where(AuditLog.created_at < audit_cutoff)
    )
    results["audit_logs_deleted"] = result.rowcount
    
    await db.commit()
    
    logger.info(
        "cleanup_executed",
        user_id=current_user.id,
        results=results
    )
    
    return {
        "message": "Cleanup completed successfully",
        "details": results
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Estatísticas do banco de dados"""
    stats = {}
    
    # Contagem de tabelas principais
    tables = [
        "tenants", "users", "employees", "rubrics",
        "competencies", "competency_items", "payments",
        "attachments", "refresh_tokens", "audit_log"
    ]
    
    for table in tables:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        stats[table] = result.scalar()
    
    # Tamanho total dos attachments
    result = await db.execute(text("SELECT SUM(size) FROM attachments"))
    stats["total_attachments_size_bytes"] = result.scalar() or 0
    
    # Tokens ativos
    result = await db.execute(
        text(
            "SELECT COUNT(*) FROM refresh_tokens "
            "WHERE expires_at > NOW() AND revoked = false"
        )
    )
    stats["active_tokens"] = result.scalar()
    
    return stats
