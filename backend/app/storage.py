from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from app.config import settings
import hashlib
import uuid


class MinIOService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Garante que o bucket existe"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
        except S3Error as e:
            print(f"Error creating bucket: {e}")
    
    def generate_presigned_url(
        self,
        filename: str,
        content_type: str,
        tenant_id: int
    ) -> tuple[str, str]:
        """
        Gera URL assinada para upload
        Returns: (upload_url, object_key)
        """
        # Gerar chave única
        file_id = str(uuid.uuid4())
        extension = filename.split('.')[-1] if '.' in filename else ''
        object_key = f"tenant_{tenant_id}/{file_id}.{extension}" if extension else f"tenant_{tenant_id}/{file_id}"
        
        # Gerar URL assinada para PUT
        url = self.client.presigned_put_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(minutes=30)
        )
        
        return url, object_key

    def put_object(self, object_key: str, data: bytes, content_type: str) -> dict:
        """Upload direto de bytes"""
        import io
        stream = io.BytesIO(data)
        result = self.client.put_object(
            settings.MINIO_BUCKET,
            object_key,
            stream,
            length=len(data),
            content_type=content_type
        )
        return {
            "etag": result.etag,
            "version_id": result.version_id
        }

    def get_object(self, object_key: str) -> bytes:
        """Download de objeto como bytes"""
        response = None
        try:
            response = self.client.get_object(settings.MINIO_BUCKET, object_key)
            return response.read()
        finally:
            if response:
                response.close()
    
    async def download_file(self, object_key: str) -> bytes:
        """Download de arquivo como bytes (async wrapper)"""
        return self.get_object(object_key)
    
    async def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Gera URL presigned para download (async wrapper)"""
        return self.generate_presigned_get(object_key, expires_minutes=expires_in // 60)
                
    def generate_presigned_get(self, object_key: str, expires_minutes: int = 60) -> str:
        """Gera URL para download - usa URL pública direta se bucket for público"""
        # Se tiver URL pública configurada, usar acesso direto (bucket público)
        if settings.MINIO_PUBLIC_URL:
            return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{object_key}"
        
        # Fallback para URL pré-assinada
        url = self.client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(minutes=expires_minutes)
        )
        return url
    
    def generate_download_url(self, object_key: str) -> str:
        """Gera URL para download - usa URL pública direta se bucket for público"""
        # Se tiver URL pública configurada, usar acesso direto (bucket público)
        if settings.MINIO_PUBLIC_URL:
            return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{object_key}"
        
        # Fallback para URL pré-assinada
        url = self.client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(hours=1)
        )
        return url
    
    def delete_object(self, object_key: str):
        """Remove objeto do MinIO"""
        try:
            self.client.remove_object(settings.MINIO_BUCKET, object_key)
        except S3Error as e:
            print(f"Error deleting object: {e}")
    
    @staticmethod
    def calculate_sha256(file_content: bytes) -> str:
        """Calcula hash SHA256 do arquivo"""
        return hashlib.sha256(file_content).hexdigest()


minio_service = MinIOService()
