# Guia de Configuração SSL para contas.semppreonline.com.br

## Problema Identificado

O domínio `contas.semppreonline.com.br` está redirecionando para HTTPS, mas o certificado SSL ainda não foi configurado.

## Solução

### Opção 1: Configurar SSL (Recomendado para Produção)

1. **Executar o script de obtenção de SSL:**
   ```bash
   cd /opt/financeiro-pro/nginx
   bash get-ssl.sh
   ```

2. **Ativar a configuração SSL:**
   ```bash
   cd /opt/financeiro-pro/nginx/conf.d
   mv financeiro-dev.conf financeiro-dev.conf.bak
   mv financeiro.conf.ssl financeiro.conf
   docker-compose restart nginx
   ```

3. **Testar o acesso:**
   - HTTPS: https://contas.semppreonline.com.br
   - HTTP redireciona automaticamente para HTTPS

### Opção 2: Desabilitar Redirecionamento HTTPS Temporário

Se você está apenas testando e não quer SSL ainda:

1. **Verificar qual servidor Nginx externo está causando o redirect:**
   ```bash
   # Procurar por redirecionamento de HTTP para HTTPS
   grep -r "301\|redirect.*https" /etc/nginx/
   ```

2. **Desabilitar temporariamente o redirect no Nginx externo** ou acessar via:
   - IP direto: http://SEU_IP:8080
   - Localhost (se estiver na máquina): http://localhost:8080

## Status Atual

✅ **Configurações prontas:**
- Nginx configurado para HTTP (porta 8080) e HTTPS (porta 8443)
- Certbot configurado para renovação automática
- Script get-ssl.sh pronto para uso
- Configuração SSL em standby: `financeiro.conf.ssl`

⚠️ **Aguardando:**
- Obtenção do certificado SSL Let's Encrypt
- Ativação da configuração HTTPS

## Notas Importantes

1. O DNS do domínio já está apontando para o servidor correto
2. O certificado Let's Encrypt será renovado automaticamente a cada 12h
3. Após configurar SSL, o HTTP (porta 80) redirecionará automaticamente para HTTPS (443)
4. As portas Docker são 8080/8443, mas você pode mapear para 80/443 no docker-compose.yml se preferir
