#!/bin/bash

# Script de verificação pré-deploy
# Verifica se tudo está configurado corretamente

set -e

echo "🔍 Verificando configuração do Financeiro Pro..."
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

errors=0
warnings=0

# Função para verificar
check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ((errors++))
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((warnings++))
}

# 1. Verificar Docker
echo "📦 Verificando Docker..."
docker --version > /dev/null 2>&1
check $? "Docker instalado"

docker-compose --version > /dev/null 2>&1
check $? "Docker Compose instalado"

docker info > /dev/null 2>&1
check $? "Docker rodando"

# 2. Verificar arquivos essenciais
echo ""
echo "📁 Verificando arquivos..."
[ -f "docker-compose.yml" ]
check $? "docker-compose.yml existe"

[ -f "backend/requirements.txt" ]
check $? "backend/requirements.txt existe"

[ -f "frontend/package.json" ]
check $? "frontend/package.json existe"

[ -f "backend/.env.example" ]
check $? "backend/.env.example existe"

# 3. Verificar .env
echo ""
echo "⚙️  Verificando configuração..."
if [ -f "backend/.env" ]; then
    check 0 "backend/.env existe"
    
    # Verificar SECRET_KEY
    if grep -q "change-me-in-production" backend/.env; then
        warn "SECRET_KEY ainda é o padrão! Execute: openssl rand -hex 32"
    else
        check 0 "SECRET_KEY foi alterada"
    fi
else
    warn "backend/.env não existe (será criado pelo deploy.sh)"
fi

# 4. Verificar scripts executáveis
echo ""
echo "🔧 Verificando scripts..."
[ -x "deploy.sh" ]
check $? "deploy.sh é executável"

[ -x "nginx/get-ssl.sh" ]
check $? "nginx/get-ssl.sh é executável"

[ -x "scripts/backup.sh" ]
check $? "scripts/backup.sh é executável"

# 5. Verificar portas disponíveis
echo ""
echo "🔌 Verificando portas..."
! nc -z localhost 80 > /dev/null 2>&1
check $? "Porta 80 disponível"

! nc -z localhost 443 > /dev/null 2>&1
check $? "Porta 443 disponível"

! nc -z localhost 8000 > /dev/null 2>&1
check $? "Porta 8000 disponível"

! nc -z localhost 3000 > /dev/null 2>&1
check $? "Porta 3000 disponível"

! nc -z localhost 5432 > /dev/null 2>&1
check $? "Porta 5432 disponível"

! nc -z localhost 9000 > /dev/null 2>&1
check $? "Porta 9000 disponível"

# 6. Verificar espaço em disco
echo ""
echo "💾 Verificando espaço em disco..."
available=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ $available -gt 10 ]; then
    check 0 "Espaço em disco suficiente (${available}GB disponível)"
else
    warn "Pouco espaço em disco (${available}GB disponível, recomendado: >10GB)"
fi

# 7. Verificar RAM
echo ""
echo "🧠 Verificando memória RAM..."
total_ram=$(free -g | awk '/^Mem:/{print $2}')
if [ $total_ram -gt 2 ]; then
    check 0 "RAM suficiente (${total_ram}GB)"
else
    warn "Pouca RAM (${total_ram}GB, recomendado: >2GB)"
fi

# Resumo
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ Verificação concluída com sucesso!${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}⚠ $warnings avisos (revise)${NC}"
    fi
    echo ""
    echo "Próximo passo:"
    echo "  ./deploy.sh"
    exit 0
else
    echo -e "${RED}✗ $errors erros encontrados${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}⚠ $warnings avisos${NC}"
    fi
    echo ""
    echo "Corrija os erros antes de continuar."
    exit 1
fi
