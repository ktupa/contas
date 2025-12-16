# 🚀 Quick Start - Financeiro Pro

## Instalação em 3 passos

### 1️⃣ Setup do Servidor (primeira vez)

```bash
cd /opt/financeiro-pro
chmod +x scripts/setup-server.sh
sudo ./scripts/setup-server.sh

# Fazer logout e login novamente
exit
```

### 2️⃣ Deploy da Aplicação

```bash
cd /opt/financeiro-pro
chmod +x deploy.sh
./deploy.sh
```

Aguarde ~2 minutos. O sistema estará disponível em:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### 3️⃣ Configurar SSL (Produção)

**Antes**: Certifique-se que o domínio `contas.semppreonline.com.br` aponta para o servidor.

```bash
# Edite o email no arquivo
nano nginx/get-ssl.sh

# Execute
chmod +x nginx/get-ssl.sh
./nginx/get-ssl.sh
```

Pronto! Acesse: https://contas.semppreonline.com.br

## 🔐 Login Inicial

```
Email:    admin@financeiro.com
Senha:    admin123
```

**⚠️ IMPORTANTE**: Altere a senha imediatamente após o primeiro login!

## 📝 Comandos Essenciais

```bash
# Ver status
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f api
docker-compose logs -f web

# Parar tudo
docker-compose down

# Reiniciar tudo
docker-compose restart

# Reiniciar apenas um serviço
docker-compose restart api

# Acessar banco de dados
docker-compose exec db psql -U financeiro -d financeiro_pro
```

## 🆘 Problemas Comuns

### API não inicia

```bash
docker-compose logs api
# Verifique se o banco está rodando
docker-compose ps db
```

### Frontend mostra erro de conexão

```bash
# Verifique a URL da API
docker-compose exec web env | grep NEXT_PUBLIC_API_URL

# Deve ser: http://contas.semppreonline.com.br/api
# Ou: http://localhost:8000 (desenvolvimento)
```

### SSL não funciona

```bash
# Verifique se o domínio está acessível
curl http://contas.semppreonline.com.br

# Verifique certificados
docker-compose exec nginx ls -la /etc/letsencrypt/live/

# Re-execute o script SSL
./nginx/get-ssl.sh
```

## 🔄 Atualizar Sistema

```bash
cd /opt/financeiro-pro

# Pull das alterações (se usando git)
git pull

# Rebuild
docker-compose build

# Executar migrações (se houver)
docker-compose run --rm api alembic upgrade head

# Reiniciar
docker-compose up -d
```

## 💾 Backup e Restore

### Backup Manual

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

Arquivos salvos em: `/backup/financeiro-pro/`

### Restore

```bash
# Parar containers
docker-compose down

# Restore do banco
gunzip < /backup/financeiro-pro/db_20251213_120000.sql.gz | \
  docker-compose exec -T db psql -U financeiro financeiro_pro

# Reiniciar
docker-compose up -d
```

## 📊 Primeira Utilização

### 1. Criar Colaboradores

Dashboard → Colaboradores → Novo Colaborador

```
Nome: João Silva
Cargo: Desenvolvedor
Regime: CLT
Centro de Custo: TI
```

### 2. Verificar Rubricas

Dashboard → Rubricas

Já vem com rubricas padrão:
- Salário Base
- Vale Refeição
- Vale Transporte
- etc.

### 3. Criar Competência do Mês

Dashboard → Competências → Nova Competência

```
Colaborador: João Silva
Mês/Ano: 12/2025
```

### 4. Adicionar Itens

Competência → Itens → Adicionar

```
Rubrica: Salário Base
Valor: R$ 5.000,00
```

### 5. Registrar Pagamentos

Competência → Pagamentos → Novo Pagamento

```
Data: hoje
Valor: R$ 2.000,00
Tipo: Adiantamento
Forma: PIX
```

### 6. Fechar Mês

Competência → Fechar Mês ✅

(Bloqueia edição - apenas admin pode reabrir)

## 📈 Monitoramento

### Verificar Saúde dos Serviços

```bash
# API
curl http://localhost:8000/health

# MinIO
curl http://localhost:9000/minio/health/live

# PostgreSQL
docker-compose exec db pg_isready
```

### Ver Estatísticas

Login como admin → Fazer request:

```bash
curl -X GET http://localhost:8000/maintenance/stats \
  -H "Authorization: Bearer SEU_TOKEN"
```

### Limpeza Manual

```bash
curl -X POST http://localhost:8000/maintenance/cleanup \
  -H "Authorization: Bearer SEU_TOKEN"
```

## 🎯 Fluxo Completo de Uso

```
1. Cadastrar Colaborador (RH)
2. Criar Competência do Mês (Financeiro)
3. Clonar itens do mês anterior (se houver)
4. Ajustar valores se necessário
5. Registrar pagamentos conforme ocorrem
6. Upload de comprovantes
7. Verificar resumo/dashboard
8. Fechar mês quando completo
9. Gerar relatórios
```

## 🔒 Segurança

### Alterar Senha do Admin

```bash
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash
from sqlalchemy import select

async def change_password():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == "admin@financeiro.com")
        )
        user = result.scalar_one()
        user.password_hash = get_password_hash("NOVA_SENHA_FORTE")
        await db.commit()
        print("Senha alterada!")

asyncio.run(change_password())
EOF
```

### Alterar SECRET_KEY

```bash
# Gerar nova chave
openssl rand -hex 32

# Editar .env
nano backend/.env
# SECRET_KEY=nova_chave_aqui

# Reiniciar API
docker-compose restart api
```

## 📱 Acessos Rápidos

- **Frontend**: https://contas.semppreonline.com.br
- **API Docs**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc
- **MinIO Console**: http://localhost:9001
- **Logs API**: `docker-compose logs -f api`

## 💡 Dicas

1. **Performance**: Monitore uso de RAM/CPU com `docker stats`
2. **Backup**: Configure cron semanal (já incluído no setup)
3. **SSL**: Certificados renovam automaticamente
4. **Logs**: Rotacione logs do Nginx regularmente
5. **Segurança**: Use senhas fortes e diferentes em produção

## 📞 Suporte

Problemas? Verifique:
1. Logs dos containers
2. README.md completo
3. ARCHITECTURE.md para detalhes técnicos

---

**Sucesso! 🎉**
