"""
Serviço de criptografia para senhas de certificados digitais
Usa AES-GCM para criptografia simétrica
"""
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import os
import base64
import logging

logger = logging.getLogger(__name__)


class CryptoService:
    """Serviço para criptografar/descriptografar senhas de certificados"""
    
    def __init__(self, master_key: str):
        """
        Inicializa o serviço com a chave master
        
        Args:
            master_key: Chave master em base64 (32 bytes quando decodificada)
        """
        try:
            # Decodifica a chave master de base64
            self.key = base64.b64decode(master_key)
            if len(self.key) != 32:
                raise ValueError("Master key deve ter 32 bytes (256 bits)")
            self.aesgcm = AESGCM(self.key)
        except Exception as e:
            logger.error(f"Erro ao inicializar CryptoService: {e}")
            raise ValueError(f"Chave master inválida: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Criptografa um texto usando AES-GCM
        
        Args:
            plaintext: Texto a ser criptografado
            
        Returns:
            String base64 contendo nonce + ciphertext + tag
        """
        try:
            # Gera um nonce aleatório de 12 bytes (96 bits)
            nonce = os.urandom(12)
            
            # Criptografa o texto
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # Combina nonce + ciphertext e codifica em base64
            encrypted = nonce + ciphertext
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Erro ao criptografar: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        Descriptografa um texto criptografado com AES-GCM
        
        Args:
            encrypted: String base64 contendo nonce + ciphertext + tag
            
        Returns:
            Texto descriptografado
        """
        try:
            # Decodifica de base64
            encrypted_bytes = base64.b64decode(encrypted)
            
            # Separa nonce (12 bytes) do ciphertext
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            # Descriptografa
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Erro ao descriptografar: {e}")
            raise


def generate_master_key() -> str:
    """
    Gera uma nova chave master aleatória
    
    Returns:
        Chave master em base64 (32 bytes)
    """
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode('utf-8')


# Teste básico
if __name__ == "__main__":
    # Gera uma chave de teste
    test_key = generate_master_key()
    print(f"Master Key (adicione ao .env): {test_key}")
    
    # Testa criptografia
    crypto = CryptoService(test_key)
    password = "MinhaSenhaSecreta123!"
    
    encrypted = crypto.encrypt(password)
    print(f"Criptografado: {encrypted}")
    
    decrypted = crypto.decrypt(encrypted)
    print(f"Descriptografado: {decrypted}")
    
    assert password == decrypted, "Erro: senha descriptografada não confere!"
    print("✓ Teste OK")
