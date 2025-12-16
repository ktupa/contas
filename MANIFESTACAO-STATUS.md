# Status da Implementação de Manifestação do Destinatário

## ✅ Componentes Implementados

### 1. Backend - SEFAZ Cliente de Eventos
- **Arquivo**: `backend/app/sefaz_evento_client.py`
- **Funcionalidades**:
  - Cliente SOAP para NFeRecepcaoEvento4
  - Suporte a SOAP 1.2 (namespace correto)
  - Endpoints por UF (mapeamento completo)
  - Assinatura digital com SHA256/RSA-SHA256
  - Certificado A1 (PFX) por empresa
  - Tipos de evento: 210210 (Ciência), 210200 (Confirmação), 210220 (Desconhecimento), 210240 (Operação não Realizada)

### 2. Backend - Serviço de Manifestação
- **Arquivo**: `backend/app/manifestacao_service.py`
- **Fluxo**:
  1. Tenta buscar XML completo (pode já estar disponível)
  2. Envia manifestação para SEFAZ
  3. Reconsulta DF-e para obter procNFe
  4. Registra tentativas e status no banco
- **Recursos**:
  - Anti-blocking (respeita throttling da SEFAZ)
  - Retry automático
  - Tracking de status (pending, sent, accepted, error)

### 3. Database
- **Migration**: `012_add_manifestations_and_xml_kind.py`
- **Tabelas**:
  - `nfe_manifestations`: Registro de tentativas de manifestação
  - Campo `xml_kind` em `nfe_documents` (summary/full)
  - Campo `last_cstat` em `sefaz_dfe_state` (anti-blocking)

### 4. API Endpoints
- `POST /fiscal/nfe/resolve/{company_id}` - Resolve todas as notas summary de uma empresa
- `POST /fiscal/nfe/resolve/{company_id}/{chave}` - Resolve uma nota específica

### 5. Frontend
- **Arquivo**: `frontend/app/fiscal/notas/page.tsx`
- **UI**:
  - Badge verde/amarelo para XML Completo/Resumo
  - Botão de resolver por linha
  - Modal com CTA para resolver XMLs resumidos
  - Função de resolução em massa

## ⚠️ Status Atual: cStat 215 - Falha no Schema XML

### Testes Realizados
- ✅ Certificado A1 carregado e enviado via HTTPS
- ✅ Endpoint correto por UF (Goiás)
- ✅ SOAP 1.2 com namespace correto
- ✅ Assinatura digital SHA256
- ✅ XML bem formado
- ❌ **SEFAZ retorna cStat 215: "Rejeição: Falha no schema XML"**

### XML Enviado (Última Versão)
```xml
<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <idLote>1</idLote>
  <evento versao="1.00">
    <infEvento Id="ID210210{chave}01">
      <cOrgao>52</cOrgao>
      <tpAmb>1</tpAmb>
      <CNPJ>20106310000100</CNPJ>
      <chNFe>{chave}</chNFe>
      <dhEvento>2025-12-16T10:44:46-03:00</dhEvento>
      <tpEvento>210210</tpEvento>
      <nSeqEvento>1</nSeqEvento>
      <verEvento>1.00</verEvento>
      <detEvento versao="1.00">
        <descEvento>Ciencia da Operacao</descEvento>
      </detEvento>
      <Signature>...</Signature>
    </infEvento>
  </evento>
</envEvento>
```

### Possíveis Causas do Erro 215

1. **Credenciamento**: Empresa pode precisar estar credenciada na SEFAZ-GO para manifestação
2. **Homologação vs Produção**: Ambiente de homologação pode não suportar todos os serviços
3. **Formato de dhEvento**: Pode exigir formato específico (testados: UTC+Z, -03:00)
4. **Namespace do detEvento**: Pode requerer declaração explícita
5. **Versão do Schema**: GO pode estar usando versão específica do XSD

## 📋 Próximos Passos Recomendados

### Validação
1. **Testar com Certificado Homologado**
   - Verificar se o certificado está habilitado para manifestação na SEFAZ-GO
   - Consultar portal da SEFAZ-GO sobre requisitos de credenciamento

2. **Validar XML contra XSD Oficial**
   - Download do schema: http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=py/B7YvxWPc=
   - Usar ferramenta de validação XSD

3. **Testar Endpoint Alternativo**
   - SVRS (Ambiente Virtual): pode ter regras diferentes
   - Verificar se GO aceita manifestação direta ou apenas via SVRS

### Debugging Avançado
1. Habilitar logs detalhados da SEFAZ (se disponível via portal)
2. Comparar com XML de manifestação validado de outro sistema
3. Consultar com Suporte Técnico da SEFAZ-GO

### Implementação de Fallback
1. Sistema já registra tentativas com status
2. Implementar fila para retry automático
3. Notificar usuário quando manifestação pendente por muito tempo

## 🎯 Funcionalidades Prontas para Uso

Mesmo sem manifestação automática funcionando, o sistema já oferece:

1. **Visualização de NF-e**
   - Lista com todas as notas (summary e full)
   - Badge indicando tipo de XML
   - Download de XML e PDF (quando disponível)

2. **Sync Automático**
   - Consulta periódica ao DF-e
   - Download automático de XMLs disponíveis
   - Já traz procNFe quando disponível

3. **Tracking de Manifestação**
   - Registros de tentativas
   - Status e erro messages
   - Histórico completo

## 🔧 Configurações Atuais

### Docker Compose
```yaml
NFE_AMBIENTE_PRODUCAO: "true"  # Ambiente de produção ativo
```

### Endpoints por UF
- GO: `https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4`
- SP: `https://nfe.fazenda.sp.gov.br/ws/recepcaoevento4.asmx`
- (Mapeamento completo para todas as UFs)

### SSL
- Certificados CA atualizados
- Verificação SSL desabilitada temporariamente (verify=False)
- **Recomendação**: Reativar verify=certifi.where() após testes

## 📞 Suporte

Para resolver o erro 215, recomenda-se:
1. Contatar SEFAZ-GO para verificar requisitos de manifestação
2. Validar certificado digital tem permissão para eventos
3. Testar em ambiente de homologação com suporte técnico

---

**Última atualização**: 16/12/2025
**Ambiente**: Produção
**Status**: Aguardando resolução de erro 215 da SEFAZ
