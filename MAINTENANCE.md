# 🛠️ Guia de Manutenção - Financeiro Pro

## Tarefas de Rotina

### Diárias (Automáticas)
- ✅ Limpeza de logs de auditoria (às 3h)
- ✅ Limpeza de sessões expiradas (às 3h)
- ✅ Renovação SSL (verificação)

### Semanais (Recomendadas)

#### 1. Verificar Logs
```bash
# Ver erros recentes
docker-compose logs api | grep ERROR

# Ver status dos serviços
docker-compose ps
```

#### 2. Verificar Espaço em Disco
```bash
# Espaço geral
df -h

# Uso do Docker
docker system df

# Limpar imagens não utilizadas (se necessário)
docker system prune -a
```

#### 3. Backup Manual
```bash
./scripts/backup.sh
```

### Mensais

#### 1. Atualizar Sistema
```bash
# Atualizar pacotes do sistema
sudo apt update && sudo apt upgrade -y

# Atualizar imagens Docker
docker-compose pull
docker-compose up -d
```

#### 2. Verificar Certificado SSL
```bash
# Ver validade
docker-compose exec nginx openssl x509 -in /etc/letsencrypt/live/contas.semppreonline.com.br/fullchain.pem -noout -dates

# Renovar manualmente (se necessário)
./nginx/get-ssl.sh
```

#### 3. Revisar Usuários
```bash
# Listar usuários ativos
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from sqlalchemy import select

async def list_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.active == True))
        for user in result.scalars():
            print(f"{user.id}: {user.email} ({user.role})")

asyncio.run(list_users())
EOF
```

## Solução de Problemas

### 1. Container não inicia

```bash
# Ver logs
docker-compose logs [service_name]

# Reiniciar
docker-compose restart [service_name]

# Rebuild (se necessário)
docker-compose build [service_name] --no-cache
docker-compose up -d [service_name]
```

### 2. Banco de dados lento

```bash
# Verificar queries lentas (PostgreSQL)
docker-compose exec db psql -U financeiro -d financeiro_pro << EOF
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
EOF

# Vacuum e analyze
docker-compose exec db psql -U financeiro -d financeiro_pro -c "VACUUM ANALYZE;"
```

### 3. Erro de memória

```bash
# Ver uso de memória
docker stats

# Aumentar limite no docker-compose.yml:
# services:
#   api:
#     deploy:
#       resources:
#         limits:
#           memory: 2G

docker-compose up -d
```

### 4. MinIO não acessível

```bash
# Verificar status
docker-compose exec minio curl localhost:9000/minio/health/live

# Recriar bucket
docker-compose exec api python << EOF
from app.storage import minio_service
minio_service._ensure_bucket()
print("Bucket recriado")
EOF
```

## Tarefas de Administração

### Adicionar Novo Usuário (via CLI)

```bash
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import User, Tenant
from app.auth import get_password_hash
from sqlalchemy import select

async def create_user():
    async with AsyncSessionLocal() as db:
        # Pegar primeiro tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one()
        
        user = User(
            tenant_id=tenant.id,
            name="Novo Usuário",
            email="novo@example.com",
            password_hash=get_password_hash("senha123"),
            role="financeiro",
            active=True
        )
        db.add(user)
        await db.commit()
        print(f"Usuário criado: {user.email}")

asyncio.run(create_user())
EOF
```

### Alterar Senha de Usuário

```bash
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from app.auth import get_password_hash
from sqlalchemy import select

async def change_password(email, new_password):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.password_hash = get_password_hash(new_password)
        await db.commit()
        print(f"Senha alterada para: {user.email}")

asyncio.run(change_password("admin@financeiro.com", "NOVA_SENHA_FORTE"))
EOF
```

### Limpar Dados Antigos Manualmente

```bash
# Via API (requer autenticação admin)
curl -X POST https://contas.semppreonline.com.br/api/maintenance/cleanup \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"

# Via CLI
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import RefreshToken, AuditLog
from sqlalchemy import delete
from datetime import datetime, timedelta

async def cleanup():
    async with AsyncSessionLocal() as db:
        # Tokens
        cutoff = datetime.utcnow() - timedelta(days=90)
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.created_at < cutoff)
        )
        print(f"Tokens removidos: {result.rowcount}")
        
        # Logs
        cutoff = datetime.utcnow() - timedelta(days=180)
        result = await db.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        print(f"Logs removidos: {result.rowcount}")
        
        await db.commit()

asyncio.run(cleanup())
EOF
```

## Backup e Restore

### Backup Completo

```bash
#!/bin/bash
BACKUP_DIR="/backup/financeiro-pro/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 1. PostgreSQL
docker-compose exec -T db pg_dump -U financeiro financeiro_pro | gzip > "$BACKUP_DIR/db.sql.gz"

# 2. Configurações
cp -r backend/.env "$BACKUP_DIR/"
cp -r nginx/conf.d "$BACKUP_DIR/nginx-conf"

# 3. MinIO (opcional - pode ser grande)
docker run --rm --volumes-from financeiro_minio -v $BACKUP_DIR:/backup alpine tar czf /backup/minio.tar.gz /data

# 4. Certificados SSL
sudo cp -r /var/lib/docker/volumes/financeiro-pro_certbot_conf/_data "$BACKUP_DIR/ssl"

echo "Backup completo em: $BACKUP_DIR"
```

### Restore

```bash
BACKUP_DIR="/backup/financeiro-pro/20251213_120000"

# 1. Parar serviços
docker-compose down

# 2. Restore PostgreSQL
docker-compose up -d db
sleep 10
gunzip < "$BACKUP_DIR/db.sql.gz" | docker-compose exec -T db psql -U financeiro financeiro_pro

# 3. Restore configurações
cp "$BACKUP_DIR/.env" backend/
cp -r "$BACKUP_DIR/nginx-conf/"* nginx/conf.d/

# 4. Restore MinIO (se houver)
docker run --rm --volumes-from financeiro_minio -v $BACKUP_DIR:/backup alpine tar xzf /backup/minio.tar.gz -C /

# 5. Reiniciar tudo
docker-compose up -d

echo "Restore concluído!"
```

## Monitoramento

### Estatísticas em Tempo Real

```bash
# CPU, RAM, Network
docker stats

# Conexões ativas no PostgreSQL
docker-compose exec db psql -U financeiro -d financeiro_pro -c "SELECT count(*) FROM pg_stat_activity;"

# Tamanho do banco
docker-compose exec db psql -U financeiro -d financeiro_pro -c "SELECT pg_size_pretty(pg_database_size('financeiro_pro'));"

# Espaço usado por tabela
docker-compose exec db psql -U financeiro -d financeiro_pro -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

### Logs Estruturados

```bash
# Buscar erros específicos
docker-compose logs api | grep '"level": "error"'

# Buscar ações de um usuário
docker-compose logs api | grep '"user_id": 1'

# Exportar logs para arquivo
docker-compose logs --no-color api > logs_$(date +%Y%m%d).txt
```

## Atualizações

### Atualizar Código (Git)

```bash
cd /opt/financeiro-pro

# Backup antes de atualizar
./scripts/backup.sh

# Pull
git pull

# Rebuild
docker-compose build

# Migrations (se houver)
docker-compose run --rm api alembic upgrade head

# Reiniciar
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

### Rollback

```bash
# Parar serviços
docker-compose down

# Voltar código
git checkout COMMIT_ANTERIOR

# Rebuild
docker-compose build

# Rollback migrations (se necessário)
docker-compose run --rm api alembic downgrade -1

# Reiniciar
docker-compose up -d
```

## Segurança

### Rotação de Senhas

```bash
# 1. SECRET_KEY (requer restart)
openssl rand -hex 32  # Copiar nova chave
nano backend/.env     # Atualizar SECRET_KEY
docker-compose restart api

# 2. PostgreSQL
docker-compose exec db psql -U financeiro -d postgres -c "ALTER USER financeiro WITH PASSWORD 'NOVA_SENHA';"
# Atualizar backend/.env e docker-compose.yml
docker-compose restart db api

# 3. MinIO
# Atualizar em docker-compose.yml e backend/.env
docker-compose restart minio api
```

### Audit de Segurança

```bash
# Verificar permissões de arquivos
find . -type f -perm /o+w

# Verificar imagens vulneráveis
docker scan financeiro-pro-api

# Revisar logs de autenticação
docker-compose exec api python << EOF
import asyncio
from app.database import AsyncSessionLocal
from app.models import AuditLog
from sqlalchemy import select
from datetime import datetime, timedelta

async def audit():
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.action.like('%login%'))
            .where(AuditLog.created_at > cutoff)
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        )
        for log in result.scalars():
            print(f"{log.created_at}: {log.action} - User {log.user_id} from {log.ip_address}")

asyncio.run(audit())
EOF
```

## Checklist de Saúde

Execute mensalmente:

- [ ] Backup completo realizado
- [ ] Logs revisados (sem erros críticos)
- [ ] Espaço em disco >20% livre
- [ ] SSL válido por >30 dias
- [ ] Todas as senhas rotacionadas nos últimos 90 dias
- [ ] Sistema operacional atualizado
- [ ] Docker atualizado
- [ ] Imagens Docker atualizadas
- [ ] Metrics de performance OK
- [ ] Teste de restore de backup

---

**Mantenha este guia atualizado conforme o sistema evolui!**
