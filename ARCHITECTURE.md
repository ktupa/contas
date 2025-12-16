# Documentação Técnica - Financeiro Pro

## Arquitetura do Sistema

### Visão Geral

```
┌─────────────────┐
│   Nginx (443)   │ ← SSL/TLS Termination
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
┌───▼────┐ ┌──▼─────┐
│Frontend│ │   API  │
│Next.js │ │FastAPI │
└───┬────┘ └──┬─────┘
    │         │
    │    ┌────┴──────┬──────────┐
    │    │           │          │
    │ ┌──▼──┐    ┌──▼──┐   ┌──▼───┐
    │ │ DB  │    │MinIO│   │Certbot│
    │ │PG16 │    │ S3  │   │ SSL  │
    └─┴─────┴────┴─────┴───┴──────┘
```

### Componentes

1. **Nginx** (Port 80/443)
   - Reverse proxy
   - SSL termination
   - Static file serving
   - Load balancing ready

2. **Frontend - Next.js** (Port 3000)
   - App Router (Server Components)
   - Mantine UI components
   - Client-side state (Zustand)
   - TypeScript

3. **Backend - FastAPI** (Port 8000)
   - Async/await (asyncpg)
   - SQLAlchemy 2.0 ORM
   - Pydantic v2 validation
   - Structured logging
   - Background jobs (APScheduler)

4. **PostgreSQL 16** (Port 5432)
   - Persistent volume
   - Connection pooling
   - Partitioned tables (audit_log)

5. **MinIO** (Port 9000/9001)
   - S3-compatible storage
   - Object metadata in DB
   - Presigned URLs

## Estratégias Anti "Encher Disco"

### 1. Arquivos no MinIO (Não no Banco)

```python
# ❌ ERRADO - Salvar arquivo no banco
attachment = Attachment(file_content=binary_data)

# ✅ CORRETO - Salvar no MinIO, metadata no banco
url, key = minio_service.generate_presigned_url(...)
# Cliente faz upload direto no MinIO
attachment = Attachment(key=key, size=size, sha256=hash)
```

**Economia**: Banco não cresce com arquivos (GB → MB)

### 2. Particionamento de Auditoria

```sql
-- Tabela mãe
CREATE TABLE audit_log (...) PARTITION BY RANGE (created_at);

-- Partições mensais
CREATE TABLE audit_log_y2025m12 PARTITION OF audit_log
  FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

**Vantagens**:
- Drop de partição inteira (rápido)
- Queries mais eficientes
- Backup seletivo

### 3. Job de Limpeza Automático

```python
# Executa diariamente às 3h
@scheduler.scheduled_job('cron', hour=3, minute=0)
async def cleanup_old_data():
    # Remove logs > 180 dias
    DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '180 days';
    
    # Remove tokens expirados > 90 dias
    DELETE FROM refresh_tokens 
    WHERE (expires_at < NOW()) 
       OR (revoked = true AND created_at < NOW() - INTERVAL '90 days');
```

**Política**:
- Audit logs: 180 dias
- Sessões: 90 dias
- Dados financeiros: PERMANENTE

### 4. Colunas Enxutas

```python
# ❌ EVITAR - Guardar payload gigante
logs_json = Column(JSON)  # 100KB+ por registro

# ✅ PREFERIR - Campos específicos
action = Column(String(100))
entity_type = Column(String(50))
changes = Column(JSON)  # Apenas diff, não payload completo
```

## Modelo de Dados

### Relacionamentos Principais

```
tenants (1) ─┬─ (N) users
             ├─ (N) employees ─── (N) competencies ─┬─ (N) competency_items
             ├─ (N) rubrics                         └─ (N) payments
             └─ (N) attachments
```

### Índices Críticos

```sql
-- Performance em queries multi-tenant
CREATE INDEX idx_competencies_tenant_employee 
  ON competencies(tenant_id, employee_id);

-- Filtros de status
CREATE INDEX idx_payments_status ON payments(status);

-- Limpeza eficiente
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
```

### Constraints Importantes

```sql
-- Unicidade por mês
ALTER TABLE competencies ADD CONSTRAINT uq_competency_employee_month
  UNIQUE (tenant_id, employee_id, year, month);

-- Isolamento multi-tenant
ALTER TABLE users ADD CONSTRAINT uq_tenant_email
  UNIQUE (tenant_id, email);
```

## Autenticação e Autorização

### JWT Flow

```
1. Login
   POST /auth/login
   → access_token (30min) + refresh_token (7 dias)

2. Request Autenticado
   GET /employees
   Header: Authorization: Bearer {access_token}

3. Refresh
   POST /auth/refresh
   Body: { refresh_token }
   → Novos tokens
```

### RBAC Implementation

```python
@router.post("/competencies/{id}/close")
async def close_competency(
    current_user: User = Depends(require_role("admin", "financeiro"))
):
    # Apenas admin e financeiro podem fechar mês
```

**Roles**:
- `admin`: Tudo + manutenção
- `financeiro`: CUD financeiro
- `rh`: CUD colaboradores + competências
- `leitura`: Read-only

## Upload de Arquivos (MinIO)

### Fluxo Completo

```
┌──────────┐  1. Request Upload     ┌─────────┐
│ Frontend │ ──────────────────────→ │   API   │
└──────────┘                         └────┬────┘
                                          │ 2. Generate
     ↑                                    │    Presigned URL
     │                                    ↓
     │ 3. Presigned URL            ┌──────────┐
     │←───────────────────────────│  MinIO   │
     │                             └──────────┘
     │ 4. Upload direto (PUT)           ↑
     └──────────────────────────────────┘
     
     │ 5. Commit metadata          ┌─────────┐
     └─────────────────────────────→│   DB    │
                                     └─────────┘
```

### Código

```typescript
// 1. Frontend pede URL
const { upload_url, object_key } = await api.post('/attachments/presign', {
  entity_type: 'payment',
  entity_id: 123,
  filename: 'comprovante.pdf',
  content_type: 'application/pdf'
});

// 2. Upload direto no MinIO
await fetch(upload_url, { method: 'PUT', body: file });

// 3. Confirma no backend
await api.post('/attachments/commit', {
  entity_type: 'payment',
  entity_id: 123,
  object_key: object_key,
  size: file.size,
  sha256: hash,
  mime: 'application/pdf'
});
```

## Cálculo de Adiantamento

### Regra de Negócio

- **Limite 40%**: Normal
- **40% a 50%**: Exceção (requer justificativa)
- **> 50%**: Bloqueado

### Implementação

```python
def check_adiantamento_limit(total_base: float, amount: float):
    percentage = amount / total_base
    
    if percentage > 0.50:
        raise HTTPException(400, "Limite de 50% excedido")
    
    if percentage > 0.40:
        if not exception_reason:
            raise HTTPException(400, "Justificativa obrigatória > 40%")
        
        return f"Exceção: {percentage*100:.1f}% - {exception_reason}"
```

## Performance e Otimização

### Database Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,        # Conexões permanentes
    max_overflow=10,    # Conexões temporárias
    pool_pre_ping=True  # Verifica conexão antes de usar
)
```

### Eager Loading (Evitar N+1)

```python
# ❌ N+1 problem
competencies = await db.execute(select(Competency))
for comp in competencies:
    employee = await db.get(Employee, comp.employee_id)  # N queries!

# ✅ Join/selectinload
from sqlalchemy.orm import selectinload
competencies = await db.execute(
    select(Competency).options(selectinload(Competency.employee))
)
```

### Frontend - React Optimization

```typescript
// Memoização
const totals = useMemo(() => calculateTotals(data), [data]);

// Lazy loading de páginas
const Dashboard = lazy(() => import('./Dashboard'));
```

## Monitoramento e Logs

### Logs Estruturados

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "payment_created",
    user_id=user.id,
    competency_id=comp_id,
    amount=payment.amount,
    kind=payment.kind
)

# Output JSON:
# {
#   "event": "payment_created",
#   "timestamp": "2025-12-13T10:30:00Z",
#   "level": "info",
#   "user_id": 1,
#   "competency_id": 42,
#   "amount": 1500.00,
#   "kind": "adiantamento"
# }
```

### Healthchecks

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Segurança

### SQL Injection Prevention

```python
# ✅ SQLAlchemy ORM (safe)
await db.execute(select(User).where(User.email == email))

# ✅ Parametrized query (safe)
await db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})

# ❌ String concatenation (UNSAFE!)
await db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 2^12 iterations
)

hash = pwd_context.hash("password123")  # $2b$12$...
```

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://contas.semppreonline.com.br"],  # Produção
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Deployment Checklist

### Antes de Produção

- [ ] Alterar SECRET_KEY
- [ ] Alterar senhas (DB, MinIO, usuários)
- [ ] Configurar CORS específico
- [ ] Obter certificado SSL
- [ ] Configurar backup automático
- [ ] Limitar taxa de requests (rate limiting)
- [ ] Configurar firewall
- [ ] Habilitar HTTPS only
- [ ] Revisar logs sensíveis
- [ ] Testar disaster recovery

### Manutenção

```bash
# Backup semanal (cron)
0 2 * * 0 /opt/financeiro-pro/scripts/backup.sh

# Verificar espaço em disco
df -h

# Monitorar logs
docker-compose logs -f --tail=100 api

# Estatísticas do banco
docker-compose exec api curl localhost:8000/maintenance/stats
```

## Troubleshooting Comum

### 1. Out of Memory
```bash
# Aumentar limite do container
docker-compose.yml:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 2. Deadlock no PostgreSQL
```sql
-- Verificar locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Matar processo
SELECT pg_terminate_backend(pid);
```

### 3. MinIO connection refused
```bash
# Verificar health
docker-compose exec minio curl localhost:9000/minio/health/live

# Recriar bucket
docker-compose exec api python -c "from app.storage import minio_service; minio_service._ensure_bucket()"
```

---

**Última atualização**: 13/12/2025
