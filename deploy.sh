#!/bin/bash

# Script de deployment completo do Financeiro Pro

set -e

echo "🚀 Iniciando deployment do Financeiro Pro..."

# 1. Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# 2. Criar arquivo .env se não existir
if [ ! -f backend/.env ]; then
    echo "📝 Criando arquivo .env..."
    cp backend/.env.example backend/.env
    
    # Gerar SECRET_KEY aleatória
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/change-me-in-production-use-openssl-rand-hex-32/$SECRET_KEY/g" backend/.env
fi

# 3. Build das imagens
echo "🏗️  Buildando imagens Docker..."
docker-compose build

# 4. Iniciar serviços de infraestrutura primeiro
echo "🗄️  Iniciando banco de dados e MinIO..."
docker-compose up -d db minio

# Aguardar banco de dados estar pronto
echo "⏳ Aguardando banco de dados..."
sleep 10

# 5. Rodar migrações
echo "📊 Executando migrações do banco de dados..."
docker-compose run --rm api alembic upgrade head

# 6. Executar seeds
echo "🌱 Executando seeds (dados iniciais)..."
docker-compose run --rm api python seeds.py

# 7. Iniciar todos os serviços
echo "🚀 Iniciando todos os serviços..."
docker-compose up -d

# 8. Aguardar serviços estarem prontos
echo "⏳ Aguardando serviços ficarem prontos..."
sleep 15

# 9. Obter certificado SSL (comentado por padrão - descomente para produção)
# echo "🔐 Obtendo certificado SSL..."
# chmod +x nginx/get-ssl.sh
# ./nginx/get-ssl.sh

echo ""
echo "✅ Deployment concluído com sucesso!"
echo ""
echo "📋 Informações importantes:"
echo "  - Frontend: https://contas.semppreonline.com.br (ou http://localhost:3000)"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - MinIO Console: http://localhost:9001"
echo ""
echo "👤 Credenciais padrão:"
echo "  - Admin: admin@financeiro.com / admin123"
echo "  - Financeiro: financeiro@financeiro.com / financeiro123"
echo "  - MinIO: minioadmin / minioadmin123"
echo ""
echo "🔧 Comandos úteis:"
echo "  - Ver logs: docker-compose logs -f [servico]"
echo "  - Parar: docker-compose down"
echo "  - Reiniciar: docker-compose restart [servico]"
echo ""
