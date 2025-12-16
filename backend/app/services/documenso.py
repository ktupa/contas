import httpx
import logging
import base64
from typing import List, Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class DocumensoClient:
    def __init__(self):
        self.base_url = settings.DOCUMENSO_API_URL.rstrip('/')
        self.api_key = settings.DOCUMENSO_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_document(self, title: str, external_id: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Cria um documento no Documenso enviando o PDF em Base64.
        """
        url = f"{self.base_url}/documents"
        
        # Converter bytes para base64 string
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        payload = {
            "title": title,
            "externalId": external_id,
            "documentBase64": pdf_base64
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro ao criar documento no Documenso: {e.response.text}")
                raise

    async def add_recipient(self, document_id: int, email: str, name: str, role: str = "SIGNER") -> Dict[str, Any]:
        """
        Adiciona um destinatário (assinante) ao documento.
        """
        url = f"{self.base_url}/documents/{document_id}/recipients"
        payload = {
            "email": email,
            "name": name,
            "role": role
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro ao adicionar destinatário {email}: {e.response.text}")
                raise

    async def add_field(self, document_id: int, recipient_id: int, type: str, page: int, x: float, y: float, width: float, height: float) -> Dict[str, Any]:
        """
        Adiciona um campo de assinatura para um destinatário.
        """
        url = f"{self.base_url}/documents/{document_id}/fields"
        payload = {
            "recipientId": recipient_id,
            "type": type,
            "page": page,
            "positionX": x,
            "positionY": y,
            "width": width,
            "height": height
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro ao adicionar campo: {e.response.text}")
                raise

    async def send_document(self, document_id: int) -> Dict[str, Any]:
        """
        Envia o documento para assinatura.
        """
        url = f"{self.base_url}/documents/{document_id}/send"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json={}, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro ao enviar documento {document_id}: {e.response.text}")
                raise

    async def get_document(self, document_id: int) -> Dict[str, Any]:
        """
        Obtém detalhes do documento.
        """
        url = f"{self.base_url}/documents/{document_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro ao obter documento {document_id}: {e.response.text}")
                raise
