#!/bin/bash

# Script para configuração inicial do servidor

set -e

echo "🔧 Configurando servidor para Financeiro Pro..."

# 1. Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "✅ Docker já instalado"
fi

# 3. Instalar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Instalando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose já instalado"
fi

# 4. Configurar firewall
echo "🔥 Configurando firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# 5. Criar diretórios
echo "📁 Criando diretórios..."
sudo mkdir -p /backup/financeiro-pro
sudo mkdir -p /opt/financeiro-pro

# 6. Configurar swap (se não existir)
if [ ! -f /swapfile ]; then
    echo "💾 Configurando swap..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 7. Configurar cron para backup
echo "⏰ Configurando backup automático..."
(crontab -l 2>/dev/null; echo "0 2 * * 0 /opt/financeiro-pro/scripts/backup.sh") | crontab -

echo ""
echo "✅ Servidor configurado com sucesso!"
echo ""
echo "Próximos passos:"
echo "  1. Fazer logout e login novamente (para aplicar grupo Docker)"
echo "  2. Clonar o projeto em /opt/financeiro-pro"
echo "  3. Executar ./deploy.sh"
echo ""
