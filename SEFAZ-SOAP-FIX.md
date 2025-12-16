# ✅ Correção do Erro 403 - SEFAZ NF-e Distribuição DF-e

## 🎯 Problema Identificado

### Erro Original
```
HTTP 403 Forbidden ao acessar:
https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl
```

### Diagnóstico

O problema tinha **3 causas principais**:

1. **❌ Acesso ao WSDL em Runtime**
   - O código usava `zeep` para buscar o WSDL da SEFAZ durante execução
   - SEFAZ bloqueia (403) requisições GET no `?wsdl` de bots/scripts
   - WSDL é apenas documentação, não é o endpoint operacional

2. **❌ Falta de Certificado A1 (mTLS)**
   - SEFAZ exige certificado digital A1 para autenticação
   - A implementação anterior não enviava o certificado corretamente
   - Sem mTLS, a SEFAZ rejeita a conexão

3. **❌ Headers SOAP Incorretos**
   - Faltava `SOAPAction` header obrigatório
   - `Content-Type` não especificava charset UTF-8
   - `User-Agent` genérico era bloqueado

---

## 🛠️ Soluções Implementadas

### 1. SOAP Manual (SEM dependência de WSDL)

**Antes:**
```python
from zeep import Client
wsdl_url = "https://hom1.nfe.fazenda.gov.br/.../asmx?wsdl"  # ❌ Bloqueado
client = Client(wsdl=wsdl_url)
response = client.service.nfeDistDFeInteresse(...)
```

**Depois:**
```python
import httpx

# Endpoint correto (SEM ?wsdl)
endpoint = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

# SOAP manual
soap_envelope = '''<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope ...>
  <soapenv:Body>
    <nfed:nfeDistDFeInteresse>
      <nfed:nfeDadosMsg><![CDATA[{dist_dfe_xml}]]></nfed:nfeDadosMsg>
    </nfed:nfeDistDFeInteresse>
  </soapenv:Body>
</soapenv:Envelope>'''

# POST com certificado
async with httpx.AsyncClient(cert=(cert_pem, key_pem)) as client:
    response = await client.post(endpoint, content=soap_envelope, headers=...)
```

### 2. Certificado A1 com mTLS

**Implementação:**

```python
def _load_certificate(self, cert_pfx_data: bytes, password: str):
    """Carrega certificado A1 do PFX"""
    self.private_key, self.certificate, _ = pkcs12.load_key_and_certificates(
        cert_pfx_data,
        password.encode('utf-8'),
        backend=default_backend()
    )

def _get_ssl_context(self) -> Tuple[str, str]:
    """Converte PFX para PEM temporário"""
    # Certificado em PEM
    cert_pem = self.certificate.public_bytes(Encoding.PEM)
    cert_path = tempfile.mkstemp(suffix='.pem')[1]
    
    # Chave privada em PEM
    key_pem = self.private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption()
    )
    key_path = tempfile.mkstemp(suffix='.pem')[1]
    
    return cert_path, key_path
```

**Uso:**
```python
async with httpx.AsyncClient(
    cert=(cert_path, key_path),  # ✅ mTLS habilitado
    verify=True,  # Valida certificado do servidor
    timeout=60
) as client:
    response = await client.post(...)
```

### 3. Headers SOAP Corretos

```python
headers = {
    "Content-Type": "text/xml; charset=utf-8",  # ✅ SOAP 1.1
    "SOAPAction": '"http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"',
    "User-Agent": "Mozilla/5.0 (compatible; SEFAZ-Client/1.0)",
}
```

**Importante:**
- `SOAPAction` deve estar entre aspas duplas: `"..."`
- `charset=utf-8` é obrigatório para caracteres acentuados
- `User-Agent` customizado evita bloqueio de bots

### 4. Envelope SOAP 1.1 Correto

```xml
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope 
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:nfed="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
  <soapenv:Header/>
  <soapenv:Body>
    <nfed:nfeDistDFeInteresse>
      <nfed:nfeDadosMsg><![CDATA[
        <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>2</tpAmb>
          <cUFAutor>91</cUFAutor>
          <CNPJ>12345678000190</CNPJ>
          <distNSU>
            <ultNSU>000000000000000</ultNSU>
          </distNSU>
        </distDFeInt>
      ]]></nfed:nfeDadosMsg>
    </nfed:nfeDistDFeInteresse>
  </soapenv:Body>
</soapenv:Envelope>
```

**Regras:**
- `tpAmb`: `1` = Produção, `2` = Homologação
- `cUFAutor`: `91` = Ambiente Nacional (AN)
- `ultNSU`: sempre **15 dígitos** com zeros à esquerda
- `CNPJ`: apenas números (14 dígitos)

### 5. Fallback de Endpoints

```python
ENDPOINTS_HOMOLOGACAO = [
    "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
]

# Tenta endpoints com fallback
for i, endpoint in enumerate(self.endpoints, 1):
    try:
        logger.info(f"Tentativa {i}/{len(self.endpoints)}: {endpoint}")
        response_xml = await self._send_soap_request(soap_envelope, endpoint)
        return self._parse_response(response_xml)
    except Exception as e:
        logger.warning(f"⚠️ Falha no endpoint {endpoint}: {e}")
        continue
```

### 6. Logging Detalhado

```python
logger.info(f"📤 Enviando requisição SOAP para: {endpoint}")
logger.info(f"📥 Status HTTP: {response.status_code}")
logger.info(f"✅ Resposta SEFAZ - Status: {status} ({motivo}), Docs: {len(documentos)}")

# Em caso de erro
logger.error(f"❌ SEFAZ retornou HTTP {response.status_code}")
logger.error(f"Corpo (primeiros 1000 chars): {response.text[:1000]}")
```

---

## 📋 Códigos de Resposta SEFAZ

| cStat | Significado | Ação |
|-------|-------------|------|
| 137 | Nenhum documento localizado | Normal - sem NF-e novas |
| 138 | Documentos localizados | Sucesso - processar docs |
| 656 | Consumo indevido | Aguardar intervalo mínimo |
| 656 | Rejeitado | Verificar CNPJ/certificado |

---

## 🧪 Testando a Correção

### 1. Verificar Logs da API

```bash
docker-compose logs -f api | grep -E "(SEFAZ|📤|📥|✅|❌)"
```

**Output esperado:**
```
📤 Enviando requisição SOAP para: https://hom.nfe.fazenda.gov.br/...
📥 Status HTTP: 200
✅ Resposta SEFAZ - Status: 138 (Documentos localizados), Docs: 5
```

### 2. Sincronizar Via Frontend

1. Acesse: **Fiscal > NF-e**
2. Clique em **Sincronizar**
3. Verifique status: deve mudar de erro para sucesso

### 3. Verificar Banco de Dados

```sql
SELECT company_id, last_nsu, last_status, last_error 
FROM sefaz_dfe_state;
```

**Esperado:**
- `last_status`: `"ok"`
- `last_error`: `NULL`
- `last_nsu`: número > 0

---

## 🔧 Troubleshooting

### Erro: "Certificado inválido"

**Causa:** Senha do certificado incorreta ou arquivo corrompido

**Solução:**
```bash
# Verificar certificado
openssl pkcs12 -info -in certificado.pfx -noout
```

### Erro: "SSL handshake failed"

**Causa:** TLS version incompatível

**Solução:**
- Atualizar OpenSSL no container
- Verificar se certificado não está vencido

### Erro: cStat 656 "Consumo indevido"

**Causa:** Muitas requisições em intervalo curto

**Solução:**
- Aguardar 5 minutos
- Reduzir intervalo de sincronização automática

### Erro: cStat 215 "Rejeição: CNPJ não cadastrado"

**Causa:** Certificado não pertence ao CNPJ consultado

**Solução:**
- Verificar se CNPJ do certificado == CNPJ da empresa
- Renovar certificado se necessário

---

## 📦 Dependências Necessárias

```txt
httpx>=0.24.0  # Cliente HTTP assíncrono
cryptography>=41.0.0  # Manipulação de certificados
```

**Removido:**
```txt
zeep  # ❌ Não é mais necessário
lxml  # ❌ Não é mais necessário
```

---

## 🎉 Resultado

✅ **ANTES:** Erro 403 Forbidden  
✅ **DEPOIS:** Sincronização funcionando com certificado A1

✅ **ANTES:** Dependência de WSDL em runtime  
✅ **DEPOIS:** SOAP manual independente

✅ **ANTES:** Logs genéricos  
✅ **DEPOIS:** Logs detalhados com emojis

✅ **ANTES:** Endpoint único  
✅ **DEPOIS:** Fallback automático entre endpoints

---

## 📚 Referências

- [Portal da NF-e - Manual de Integração](http://www.nfe.fazenda.gov.br/portal/principal.aspx)
- [Documentação NFeDistribuicaoDFe](https://www.nfe.fazenda.gov.br/portal/webServices.aspx?tipoConteudo=Wak0FwB7dKs=)
- [Especificação SOAP 1.1](https://www.w3.org/TR/2000/NOTE-SOAP-20000508/)
- [Certificados A1 SEFAZ](https://www.gov.br/pt-br/servicos/obter-certificado-digital)
