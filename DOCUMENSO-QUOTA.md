# ⚠️ Limite do Documenso Atingido

## Problema Identificado

O sistema está retornando o seguinte erro ao tentar gerar recibos para assinatura:

```
"You have reached the maximum number of documents allowed for this month"
```

Isso significa que a conta do **Documenso** (serviço de assinatura eletrônica) atingiu o **limite de documentos** do plano atual.

## O que acontece quando o limite é atingido?

✅ **Continua Funcionando:**
- O recibo PDF é gerado normalmente
- O recibo é salvo no MinIO (armazenamento)
- O recibo pode ser baixado usando o botão verde (download)
- Os dados são salvos no banco de dados

❌ **Não Funciona:**
- Link de assinatura eletrônica não é gerado
- Colaborador não recebe e-mail do Documenso
- Status fica como "PENDENTE" ao invés de "ENVIADO"

## Soluções

### Opção 1: Atualizar Plano do Documenso (Recomendado)

1. Acesse: https://app.documenso.com
2. Login com a conta configurada no sistema
3. Vá em **Settings** → **Billing**
4. Faça upgrade para um plano pago ou aguarde o próximo ciclo (reset mensal)

### Opção 2: Usar Outra Conta Documenso (Temporário)

1. Crie uma nova conta gratuita no Documenso
2. Gere uma nova API Key
3. Atualize a variável de ambiente `DOCUMENSO_API_KEY` no docker-compose.yml
4. Reinicie o container: `docker-compose restart api`

### Opção 3: Desabilitar Assinatura Eletrônica (Último Recurso)

Se não precisar de assinatura eletrônica temporariamente:

1. Remova ou comente as variáveis do Documenso no `docker-compose.yml`:
   ```yaml
   # DOCUMENSO_API_KEY: ""
   # DOCUMENSO_WEBHOOK_SECRET: ""
   ```
2. Reinicie: `docker-compose restart api`
3. Recibos serão salvos como "pending_local" (apenas download)

## Planos do Documenso

- **Gratuito**: ~5 documentos/mês
- **Pro**: ~25 documentos/mês (~$30/mês)
- **Business**: Ilimitado (~$100/mês)

## Alternativas ao Documenso

Se o Documenso não atender suas necessidades, considere:

1. **DocuSign** - Mais caro, mas mais robusto
2. **Adobe Sign** - Integrado com Adobe
3. **HelloSign/Dropbox Sign** - Fácil de usar
4. **SignRequest** - Mais barato
5. **Assinar PDF manualmente** - Sem custos, mas manual

## Como Verificar o Status

### Logs da API
```bash
docker-compose logs -f api | grep -i documenso
```

### Console do Navegador
Ao gerar um recibo, verifique no console (F12):
```javascript
📄 Resposta do generate-receipt: {
  sign_url: null,  // ← Se null = sem link de assinatura
  status: "pending_local",  // ← Status indica problema
  error_message: "Limite de documentos do Documenso atingido"
}
```

## Sistema Atualizado

O sistema agora mostra mensagens claras quando o limite é atingido:

✅ **Notificação Amigável**: Alerta laranja explicando o problema
✅ **Logs Detalhados**: Emojis e mensagens claras nos logs
✅ **Badge de Alerta**: Na página de assinaturas eletrônicas
✅ **Download Funciona**: Botão verde continua permitindo download do PDF

## Contato

Para questões sobre assinatura eletrônica:
- **Documenso Support**: support@documenso.com
- **Documentação**: https://docs.documenso.com
