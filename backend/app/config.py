from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Financeiro Pro"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # MinIO/S3
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "financeiro-attachments"
    MINIO_SECURE: bool = False
    MINIO_PUBLIC_URL: Optional[str] = None  # URL pública para downloads (ex: https://storage.seudominio.com)
    
    # Documenso (Assinatura Eletrônica)
    DOCUMENSO_API_URL: str = "https://app.documenso.com/api/v1"
    DOCUMENSO_API_KEY: Optional[str] = "api_393vivf0y77ci09a"
    DOCUMENSO_WEBHOOK_SECRET: Optional[str] = "@M3g4f0n3190"
    
    # Módulo Fiscal (NF-e)
    CERT_MASTER_KEY: str  # Chave para criptografar senhas de certificados (base64, 32 bytes)
    NFE_AMBIENTE_PRODUCAO: bool = False  # True=Produção, False=Homologação
    NFE_SYNC_INTERVAL_HOURS: int = 4  # Intervalo de sincronização automática
    
    # Retenção de dados
    AUDIT_LOG_RETENTION_DAYS: int = 180
    SESSION_RETENTION_DAYS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
