#!/bin/bash

# Script para obter certificado SSL via Let's Encrypt

DOMAIN="contas.semppreonline.com.br"
EMAIL="admin@semppreonline.com.br"  # Substitua pelo seu email

echo "🔐 Obtendo certificado SSL para $DOMAIN..."

# Certifique-se de que o Nginx está rodando
docker-compose up -d nginx

# Obter certificado
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Reiniciar Nginx para carregar o novo certificado
docker-compose restart nginx

echo "✅ Certificado SSL obtido e configurado com sucesso!"
echo "⚠️  Lembre-se: O certificado será renovado automaticamente a cada 12 horas"
