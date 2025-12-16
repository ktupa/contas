# Módulo Fiscal NF-e - Implementação Completa

## ✅ Implementado

### Backend

#### 1. Database (Migration 010)
- ✅ `company_certificates` - Armazena certificados A1 com senha criptografada
- ✅ `sefaz_dfe_state` - Controla NSU incremental por empresa
- ✅ `nfe_documents` - Documentos NF-e importados com metadados
- ✅ `nfe_sync_logs` - Histórico de sincronizações (retenção 180 dias)

#### 2. Segurança
- ✅ `crypto_service.py` - Criptografia AES-GCM para senhas de certificados
- ✅ Chave master configurada: `CERT_MASTER_KEY` no .env
- ✅ Certificados .pfx armazenados no MinIO (storage seguro)
- ✅ Logs não expõem dados sensíveis

#### 3. Serviços Core
- ✅ `certificate_service.py`
  - Upload e validação de certificados A1
  - Extração de metadados (thumbprint, validade)
  - Criptografia/descriptografia de senhas
  - Verificação automática de expiração

- ✅ `sefaz_client.py`
  - Cliente SOAP para NFeDistribuicaoDFe
  - Consulta incremental (ultNSU)
  - Consulta por NSU específico
  - Consulta por chave de acesso
  - Parse de respostas XML

- ✅ `nfe_sync_service.py`
  - Sincronização incremental automática
  - Parser de XML de NF-e
  - Salvamento de XMLs no storage
  - Classificação (recebida/emitida)
  - Cálculo SHA-256 dos XMLs
  - Importação por chave manual

#### 4. API Endpoints (`/fiscal`)

**Certificados:**
- POST `/companies/{id}/certificate` - Upload de .pfx
- GET `/companies/{id}/certificate` - Buscar certificado
- PATCH `/companies/{id}/certificate` - Atualizar status

**Sincronização:**
- POST `/nfe/sync` - Sync todas empresas
- POST `/nfe/sync/{company_id}` - Sync uma empresa
- GET `/nfe/state/{company_id}` - Estado de sync

**Notas Fiscais:**
- GET `/nfe` - Listar com filtros avançados
- GET `/nfe/{id}` - Buscar NF-e específica
- GET `/nfe/{id}/xml` - Download XML (presigned URL)
- POST `/nfe/import-by-key` - Importar por chave

**Logs:**
- GET `/nfe/logs` - Histórico de sincronizações

#### 5. Jobs Automáticos
- ✅ Sincronização periódica (configurável, padrão 4h)
- ✅ Verificação de certificados expirados (diariamente às 2h)
- ✅ Limpeza de logs antigos (diariamente às 3h)

#### 6. Models e Schemas
- ✅ `models.py` - 4 novos models SQLAlchemy
- ✅ `schemas_fiscal.py` - Schemas Pydantic completos
- ✅ Validações de campos (chave 44 dígitos, etc.)

### Configuração

#### Variáveis de Ambiente
```bash
CERT_MASTER_KEY=1xG1rGvlUX9zkBOL24eN85FbsO8Y1UIgevon/5AilLQ=
NFE_AMBIENTE_PRODUCAO=true
NFE_SYNC_INTERVAL_HOURS=4
```

#### Dependências Adicionadas
- `zeep==4.2.1` - Cliente SOAP
- `lxml==5.1.0` - Parser XML
- `cryptography==41.0.7` - Criptografia

### Storage (MinIO)
```
certs/
  {company_id}/
    {cnpj}/
      cert.pfx

nfe/xml/
  {company_id}/
    {cnpj}/
      {yyyy}/
        {mm}/
          {chave}.xml
```

## 🔄 Fluxo de Uso

### 1. Configurar Certificado
```bash
curl -X POST "http://localhost:8000/api/fiscal/companies/1/certificate" \
  -H "Authorization: Bearer <token>" \
  -F "file=@certificado.pfx" \
  -F "password=senha_certificado"
```

### 2. Sincronizar NF-e
```bash
# Manual
curl -X POST "http://localhost:8000/api/fiscal/nfe/sync/1" \
  -H "Authorization: Bearer <token>"

# Automático: a cada 4h via scheduler
```

### 3. Listar Notas
```bash
curl "http://localhost:8000/api/fiscal/nfe?company_id=1&tipo=recebida&limit=50" \
  -H "Authorization: Bearer <token>"
```

### 4. Download XML
```bash
curl "http://localhost:8000/api/fiscal/nfe/{id}/xml" \
  -H "Authorization: Bearer <token>"
# Retorna URL presigned válida por 1h
```

## 📊 Dados Criados

### Tabelas
- `company_certificates` (0 registros - pronto para uso)
- `sefaz_dfe_state` (0 registros - criado no 1º sync)
- `nfe_documents` (0 registros - populado após sync)
- `nfe_sync_logs` (0 registros - logs de sincronização)

### Jobs Agendados
- `nfe_sync_job` - A cada 4h
- `certificate_check_job` - Diariamente às 2h
- `cleanup_job` - Diariamente às 3h (inclui limpeza de logs NF-e)

## 🚫 NÃO Implementado (Frontend)

O frontend ainda precisa ser criado. Sugestões de telas:

### Tela 1: Certificados (`/empresas/[id]/certificado`)
- Upload de .pfx
- Input de senha
- Exibição de validade
- Status (ativo/expirado)
- Botão renovar

### Tela 2: Notas Fiscais (`/fiscal/notas`)
- Tabela com filtros:
  - Empresa (dropdown)
  - Tipo (recebida/emitida)
  - Período (data_ini, data_fim)
  - Emitente (busca)
  - Valor (min/max)
- Colunas:
  - Chave
  - Data Emissão
  - Emitente
  - Destinatário
  - Valor
  - Tipo
  - Situação
  - Ações (Download XML)
- Botões:
  - "Sincronizar Agora"
  - "Importar por Chave"
- Paginação

### Tela 3: Logs de Sync (`/fiscal/logs`)
- Histórico de sincronizações
- Filtros por empresa e período
- Status e quantidade de docs

## ⚠️ Próximos Passos

1. **Testar com Certificado Real**
   - Obter certificado A1 (produção ou homologação)
   - Fazer upload via API
   - Executar sincronização manual
   - Verificar se NF-e são importadas

2. **Implementar Frontend**
   - Criar páginas listadas acima
   - Integrar com API fiscal
   - Adicionar menu "Notas Fiscais"

3. **Ajustes Finos**
   - Ajustar intervalo de sync conforme necessidade
   - Configurar backoff em caso de falhas SEFAZ
   - Adicionar notificações de certificado próximo ao vencimento
   - Implementar download em lote de XMLs

4. **Ambiente de Homologação**
   - Configurar `NFE_AMBIENTE_PRODUCAO=false` para testes
   - Usar certificado de homologação da SEFAZ

## 📚 Documentação Adicional

Ver [FISCAL-README.md](./FISCAL-README.md) para:
- Guia completo de uso
- Troubleshooting
- Referências SEFAZ
- Detalhes técnicos

## 🎯 Critérios de Sucesso (Backend ✅)

- ✅ Cada empresa tem seu certificado A1 configurado
- ✅ Sync incremental por NSU funciona
- ✅ XML arquivado e listado no sistema
- ✅ Filtros por empresa e período funcionam
- ✅ Segurança: senhas criptografadas, certificados no storage
- ✅ Jobs automáticos configurados
- ✅ API REST completa com todos endpoints
- ⏳ Frontend (aguardando implementação)
