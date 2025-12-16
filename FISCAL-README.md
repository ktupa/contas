# Módulo Fiscal - NF-e

Módulo para importação e gerenciamento de Notas Fiscais Eletrônicas (NF-e) através da SEFAZ usando certificado digital A1.

## 📋 Funcionalidades

- ✅ Upload e gerenciamento de certificados digitais A1 (.pfx) por empresa
- ✅ Validação automática de certificados e verificação de expiração
- ✅ Sincronização incremental com SEFAZ via DF-e (NFeDistribuicaoDFe)
- ✅ Importação de NF-e por chave de acesso
- ✅ Listagem e filtros de notas fiscais (recebidas/emitidas)
- ✅ Download de XMLs
- ✅ Jobs automáticos de sincronização
- ✅ Segurança: senhas criptografadas com AES-GCM

## 🔐 Segurança

**Importante:** Certificados e senhas são armazenados de forma segura:

- Arquivos `.pfx` salvos no MinIO (storage)
- Senhas criptografadas com AES-GCM usando chave master
- Logs nunca expõem senhas ou dados sensíveis

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Adicione ao arquivo `.env`:

```bash
# Chave master para criptografia de senhas de certificados
# Gere uma nova chave com o comando abaixo:
CERT_MASTER_KEY=<sua_chave_base64_32_bytes>

# Ambiente SEFAZ
NFE_AMBIENTE_PRODUCAO=true  # true=Produção, false=Homologação

# Intervalo de sincronização automática (em horas)
NFE_SYNC_INTERVAL_HOURS=4
```

### 2. Gerar Chave Master

Execute o script para gerar uma nova chave master:

```bash
docker-compose exec api python -c "from app.crypto_service import generate_master_key; print(generate_master_key())"
```

Copie a chave gerada e adicione ao `.env` como `CERT_MASTER_KEY`.

### 3. Executar Migrations

```bash
docker-compose exec api alembic upgrade head
```

Isso criará as tabelas:
- `company_certificates` - Certificados digitais
- `sefaz_dfe_state` - Estado de sincronização
- `nfe_documents` - Documentos NF-e
- `nfe_sync_logs` - Logs de sincronização

## 🚀 Uso

### Cadastrar Certificado

**Endpoint:** `POST /api/fiscal/companies/{company_id}/certificate`

```bash
curl -X POST "http://localhost:8000/api/fiscal/companies/1/certificate" \
  -H "Authorization: Bearer <token>" \
  -F "file=@certificado.pfx" \
  -F "password=senha_do_certificado"
```

### Sincronizar NF-e

**Uma empresa específica:**

```bash
curl -X POST "http://localhost:8000/api/fiscal/nfe/sync/1" \
  -H "Authorization: Bearer <token>"
```

**Todas as empresas:**

```bash
curl -X POST "http://localhost:8000/api/fiscal/nfe/sync" \
  -H "Authorization: Bearer <token>"
```

### Listar Notas Fiscais

```bash
curl -X GET "http://localhost:8000/api/fiscal/nfe?company_id=1&tipo=recebida&limit=50" \
  -H "Authorization: Bearer <token>"
```

Filtros disponíveis:
- `company_id` - ID da empresa
- `tipo` - recebida, emitida, desconhecida
- `data_ini` - Data inicial (ISO format)
- `data_fim` - Data final (ISO format)
- `emitente` - Nome ou CNPJ do emitente
- `valor_min` - Valor mínimo
- `valor_max` - Valor máximo
- `skip`, `limit` - Paginação

### Importar por Chave

```bash
curl -X POST "http://localhost:8000/api/fiscal/nfe/import-by-key" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "chave": "35220812345678901234567890123456789012345678"
  }'
```

### Download de XML

```bash
curl -X GET "http://localhost:8000/api/fiscal/nfe/{nfe_id}/xml" \
  -H "Authorization: Bearer <token>"
```

Retorna uma URL presigned válida por 1 hora.

## 🔄 Sincronização Automática

### Jobs Configurados

1. **Sincronização NF-e** - A cada X horas (configurável)
   - Sincroniza todas empresas com certificado ativo
   - NSU incremental

2. **Verificação de Certificados** - Diariamente às 2h
   - Marca certificados expirados
   - Atualiza status automaticamente

3. **Limpeza de Logs** - Diariamente às 3h
   - Remove logs de sync com mais de 180 dias

### Monitorar Jobs

Verifique os logs do container:

```bash
docker-compose logs -f api | grep "nfe_sync"
```

## 📊 Estrutura de Dados

### Tabelas

**company_certificates**
- Armazena certificados A1 por empresa
- UNIQUE por company_id (1 certificado ativo por empresa)

**sefaz_dfe_state**
- Controla último NSU sincronizado
- Estado da última sincronização

**nfe_documents**
- Documentos NF-e importados
- UNIQUE por chave de acesso

**nfe_sync_logs**
- Histórico de sincronizações
- Retenção: 180 dias

### Storage (MinIO)

```
certs/{company_id}/{cnpj}/cert.pfx
nfe/xml/{company_id}/{cnpj}/{yyyy}/{mm}/{chave}.xml
```

## 🔍 Troubleshooting

### Certificado Inválido

```
Erro: "Certificado inválido: Mac verify error"
```

- Verifique se a senha está correta
- Confirme que o arquivo é .pfx válido
- Teste o certificado em outra ferramenta

### Erro de Comunicação SEFAZ

```
Erro ao consultar distribuição
```

- Verifique conectividade com SEFAZ
- Confirme que o certificado está válido
- Verifique se está usando o ambiente correto (produção/homologação)

### NSU não avança

```
last_nsu sempre retorna 0
```

- Pode não haver documentos novos
- Verifique se o CNPJ do certificado está correto
- Consulte logs de sincronização em `nfe_sync_logs`

### Certificado Expirado

Certificados expirados são marcados automaticamente pelo job diário. Para renovar:

1. Faça upload do novo certificado (mesmo endpoint)
2. O sistema substituirá o certificado anterior
3. Status mudará para "active"

## 📝 Endpoints Completos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/fiscal/companies/{id}/certificate` | Upload de certificado |
| GET | `/fiscal/companies/{id}/certificate` | Buscar certificado |
| PATCH | `/fiscal/companies/{id}/certificate` | Atualizar status |
| POST | `/fiscal/nfe/sync` | Sync todas empresas |
| POST | `/fiscal/nfe/sync/{company_id}` | Sync uma empresa |
| GET | `/fiscal/nfe/state/{company_id}` | Estado de sync |
| GET | `/fiscal/nfe` | Listar NF-e |
| GET | `/fiscal/nfe/{id}` | Buscar NF-e |
| GET | `/fiscal/nfe/{id}/xml` | Download XML |
| POST | `/fiscal/nfe/import-by-key` | Importar por chave |
| GET | `/fiscal/nfe/logs` | Logs de sync |

## 🧪 Testes

### Teste Manual - Upload de Certificado

1. Obtenha um certificado A1 de teste (.pfx)
2. Use o endpoint POST com CNPJ de homologação
3. Verifique se `status=active` e datas estão corretas

### Teste Manual - Sincronização

1. Configure `NFE_AMBIENTE_PRODUCAO=false` para homologação
2. Faça POST `/fiscal/nfe/sync/{company_id}`
3. Verifique resposta: `status=success`, `docs_found > 0`
4. Consulte `/fiscal/nfe?company_id=X`

## ⚠️ Considerações

1. **Limites SEFAZ**: Respeite os limites de requisições
2. **NSU Incremental**: SEFAZ não fornece histórico ilimitado
3. **Certificado por Empresa**: Apenas 1 certificado ativo por empresa
4. **Ambiente**: Use homologação para testes
5. **Backup**: XMLs ficam no MinIO - configure backup adequado

## 📚 Referências

- [Portal NF-e](http://www.nfe.fazenda.gov.br/)
- [Manual de Integração DF-e](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=Iy/5Qol1YbE=)
- [Schemas XML](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=/fwLvLUSmU8=)
