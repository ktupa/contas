# Módulo Fiscal - Guia de Uso

## 📋 Visão Geral

O módulo fiscal do Financeiro Pro permite a importação automática de Notas Fiscais Eletrônicas (NF-e) diretamente da SEFAZ usando certificados digitais A1.

## 🔐 Certificados Digitais

### Acessar Certificados

1. No menu lateral, clique em **Fiscal > Certificados**
2. Selecione a empresa no dropdown superior

### Upload de Certificado

1. Clique no botão **"Upload de Certificado"**
2. Selecione o arquivo `.pfx` ou `.p12` do certificado A1
3. Digite a senha do certificado
4. Clique em **"Enviar Certificado"**

### Status do Certificado

O sistema exibe:
- **Thumbprint**: Identificador único do certificado
- **Válido de**: Data inicial de validade
- **Válido até**: Data final de validade
- **Status**: Badge colorido indicando o estado:
  - 🟢 **Ativo e Válido** (verde): Certificado ativo e dentro da validade
  - 🟡 **Ativo - Vence em X dias** (amarelo): Certificado ativo mas próximo do vencimento (<30 dias)
  - 🔴 **Expirado** (vermelho): Certificado vencido
  - ⚫ **Inativo** (cinza): Certificado desativado

### Ativar/Desativar Certificado

Use o botão de **toggle** no card do certificado para ativar ou desativar.

> ⚠️ **Importante**: Apenas certificados ativos são utilizados na sincronização automática de NF-e.

## 📄 Notas Fiscais

### Acessar Notas Fiscais

1. No menu lateral, clique em **Fiscal > Notas Fiscais**
2. Selecione a empresa no dropdown superior

### Sincronização Automática

O sistema sincroniza automaticamente as NF-e a cada **4 horas** para todas as empresas com certificados ativos.

### Sincronização Manual

1. Selecione a empresa desejada
2. Clique no botão **"Sincronizar Agora"**
3. Aguarde a conclusão (uma notificação será exibida com o resultado)

### Importar por Chave de Acesso

Para importar uma NF-e específica:

1. Clique em **"Importar por Chave"**
2. Digite a chave de acesso de 44 dígitos
3. Clique em **"Importar"**

### Filtros Disponíveis

- **Empresa**: Selecione a empresa para visualizar suas notas
- **Tipo**: Filtre por notas recebidas ou emitidas
- **Buscar Emitente**: Pesquise por nome ou CNPJ do emitente
- **Período**: Selecione um intervalo de datas

### Informações Exibidas

Para cada NF-e, o sistema mostra:

- **Chave**: Chave de acesso da NF-e (primeiros 12 dígitos)
- **Tipo**: Badge indicando se é recebida ou emitida
- **Nº / Série**: Número e série da nota
- **Data Emissão**: Data de emissão
- **Emitente**: Nome e CNPJ do emitente
- **Destinatário**: Nome e CNPJ do destinatário
- **Valor**: Valor total da NF-e
- **Situação**: Status da nota (autorizada, cancelada, denegada)

### Download de XML

Clique no ícone de download para baixar o XML da NF-e.

## 🔄 Sincronização Automática

### Configuração

A sincronização automática está configurada no arquivo `docker-compose.yml`:

```yaml
NFE_SYNC_INTERVAL_HOURS: "4"  # Intervalo entre sincronizações
NFE_AMBIENTE_PRODUCAO: "true"  # true para produção, false para homologação
```

### Jobs Agendados

O sistema executa os seguintes jobs automaticamente:

1. **Sincronização de NF-e** - A cada 4 horas
   - Sincroniza NF-e de todas as empresas com certificados ativos
   - Busca apenas documentos novos (baseado no último NSU)

2. **Verificação de Certificados** - Diariamente às 02:00
   - Verifica validade de todos os certificados
   - Desativa automaticamente certificados expirados
   - Envia notificações para certificados próximos do vencimento

3. **Limpeza de Logs** - Diariamente às 03:00
   - Remove logs de sincronização com mais de 180 dias

## 📊 Logs de Sincronização

Acesse os logs via API:

```bash
GET /fiscal/nfe/sync-logs?company_id={id}&skip=0&limit=50
```

Os logs incluem:
- Data/hora da sincronização
- Empresa
- Status (success, error, partial)
- Documentos encontrados
- Documentos importados
- Mensagens de erro (se houver)

## 🔒 Segurança

### Criptografia de Senhas

As senhas dos certificados são criptografadas usando **AES-GCM** de 256 bits antes de serem armazenadas no banco de dados.

### Master Key

A chave mestra de criptografia está configurada em `CERT_MASTER_KEY` no docker-compose.yml:

```yaml
CERT_MASTER_KEY: "1xG1rGvlUX9zkBOL24eN85FbsO8Y1UIgevon/5AilLQ="
```

> ⚠️ **IMPORTANTE**: Mantenha esta chave segura! Sem ela, não será possível descriptografar as senhas dos certificados.

### Armazenamento de Certificados

Os arquivos `.pfx` são armazenados no MinIO com acesso restrito.

## 🌐 Ambientes SEFAZ

### Produção

```yaml
NFE_AMBIENTE_PRODUCAO: "true"
```

Endpoint: `https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx`

### Homologação

```yaml
NFE_AMBIENTE_PRODUCAO: "false"
```

Endpoint: `https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx`

> 💡 **Dica**: Use homologação para testes iniciais.

## 🐛 Troubleshooting

### Certificado não sincroniza

1. Verifique se o certificado está **ativo**
2. Confirme se o certificado está **dentro da validade**
3. Verifique os logs de sincronização para erros
4. Teste a senha do certificado fazendo um novo upload

### Erro "Certificado inválido ou senha incorreta"

- Verifique se o arquivo é `.pfx` ou `.p12`
- Confirme a senha digitada
- Teste o certificado em outra ferramenta

### NF-e não aparecem após sincronização

1. Verifique se há NSU disponíveis para a empresa
2. Confirme o ambiente (produção vs homologação)
3. Verifique os logs da API: `docker-compose logs api | grep fiscal`

### Erro de conexão com SEFAZ

- Verifique a conexão com a internet
- Confirme se o ambiente correto está configurado
- Verifique se o firewall permite conexões HTTPS para SEFAZ

## 📞 Suporte

Para mais informações, consulte:
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitetura do sistema
- [FISCAL-README.md](./FISCAL-README.md) - Documentação técnica do módulo
- [FISCAL-IMPLEMENTATION.md](./FISCAL-IMPLEMENTATION.md) - Detalhes de implementação

---

✨ **Desenvolvido com Next.js, FastAPI e Python**
