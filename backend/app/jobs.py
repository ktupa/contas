from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import delete, select
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.models import RefreshToken, AuditLog, NfeSyncLog, CompanyCertificate
from app.config import settings
import structlog

logger = structlog.get_logger()
scheduler = AsyncIOScheduler()


async def cleanup_old_data():
    """Job diário para limpeza de dados antigos"""
    logger.info("cleanup_job_started")
    
    async with AsyncSessionLocal() as db:
        try:
            # Limpar refresh tokens
            cutoff_date = datetime.utcnow() - timedelta(days=settings.SESSION_RETENTION_DAYS)
            
            result = await db.execute(
                delete(RefreshToken).where(
                    (RefreshToken.expires_at < datetime.utcnow()) |
                    ((RefreshToken.revoked == True) & (RefreshToken.created_at < cutoff_date))
                )
            )
            tokens_deleted = result.rowcount
            
            # Limpar audit logs
            audit_cutoff = datetime.utcnow() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
            
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < audit_cutoff)
            )
            logs_deleted = result.rowcount
            
            # Limpar logs de sincronização NF-e (180 dias)
            nfe_log_cutoff = datetime.utcnow() - timedelta(days=180)
            result = await db.execute(
                delete(NfeSyncLog).where(NfeSyncLog.started_at < nfe_log_cutoff)
            )
            nfe_logs_deleted = result.rowcount
            
            await db.commit()
            
            logger.info(
                "cleanup_job_completed",
                tokens_deleted=tokens_deleted,
                logs_deleted=logs_deleted,
                nfe_logs_deleted=nfe_logs_deleted
            )
            
        except Exception as e:
            logger.error("cleanup_job_failed", error=str(e))
            await db.rollback()


async def sync_nfe_all_companies():
    """Job periódico para sincronizar NF-e de todas as empresas"""
    logger.info("nfe_sync_job_started")
    
    async with AsyncSessionLocal() as db:
        try:
            from app.certificate_service import CertificateService
            from app.nfe_sync_service import NfeSyncService
            from app.storage import StorageService
            from app.crypto_service import CryptoService
            
            # Busca todas empresas com certificado ativo
            result = await db.execute(
                select(CompanyCertificate).where(
                    CompanyCertificate.status == 'active'
                )
            )
            certificates = result.scalars().all()
            
            if not certificates:
                logger.info("nfe_sync_job_no_certificates")
                return
            
            # Inicializa serviços
            storage = StorageService()
            crypto = CryptoService(settings.CERT_MASTER_KEY)
            cert_service = CertificateService(db, storage, crypto)
            sync_service = NfeSyncService(db, cert_service, storage)
            
            # Sincroniza cada empresa
            success_count = 0
            error_count = 0
            total_docs = 0
            
            for cert in certificates:
                try:
                    result = await sync_service.sync_company(
                        cert.company_id,
                        sync_type="incremental"
                    )
                    
                    if result['status'] == 'success':
                        success_count += 1
                        total_docs += result['docs_imported']
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(
                        "nfe_sync_company_failed",
                        company_id=cert.company_id,
                        error=str(e)
                    )
                    error_count += 1
            
            logger.info(
                "nfe_sync_job_completed",
                companies_synced=success_count,
                companies_failed=error_count,
                total_docs_imported=total_docs
            )
            
        except Exception as e:
            logger.error("nfe_sync_job_failed", error=str(e))


async def check_certificate_expiration():
    """Job diário para verificar certificados expirados"""
    logger.info("certificate_check_job_started")
    
    async with AsyncSessionLocal() as db:
        try:
            from app.certificate_service import CertificateService
            from app.storage import StorageService
            from app.crypto_service import CryptoService
            
            storage = StorageService()
            crypto = CryptoService(settings.CERT_MASTER_KEY)
            cert_service = CertificateService(db, storage, crypto)
            
            await cert_service.check_and_update_expired_certificates()
            
            logger.info("certificate_check_job_completed")
            
        except Exception as e:
            logger.error("certificate_check_job_failed", error=str(e))


def start_scheduler():
    """Inicia o scheduler de jobs"""
    # Job diário às 3h da manhã - limpeza
    scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_job",
        name="Limpeza de dados antigos",
        replace_existing=True
    )
    
    # Job periódico - sincronização NF-e (configurável, padrão 4h)
    interval_hours = settings.NFE_SYNC_INTERVAL_HOURS
    scheduler.add_job(
        sync_nfe_all_companies,
        trigger=CronTrigger(hour=f"*/{interval_hours}"),
        id="nfe_sync_job",
        name="Sincronização automática NF-e",
        replace_existing=True
    )
    
    # Job diário às 2h - verificação de certificados expirados
    scheduler.add_job(
        check_certificate_expiration,
        trigger=CronTrigger(hour=2, minute=0),
        id="certificate_check_job",
        name="Verificação de certificados",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler():
    """Para o scheduler"""
    scheduler.shutdown()
    logger.info("scheduler_stopped")
