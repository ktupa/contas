# Financeiro Pro 💰

Sistema web completo para controle financeiro e gestão de pagamentos de colaboradores, com arquitetura escalável e pronto para expansão para Contas a Pagar/Receber.

## 🚀 Tecnologias

### Backend
- **FastAPI** (Python 3.11+) - Framework web moderno e performático
- **SQLAlchemy 2.0** - ORM assíncrono
- **Alembic** - Migrations de banco de dados
- **Pydantic v2** - Validação de dados
- **PostgreSQL 16** - Banco de dados relacional
- **MinIO** - Storage S3-compatible para arquivos
- **JWT** - Autenticação e autorização
- **APScheduler** - Jobs agendados

### Frontend
- **Next.js 14** (App Router) - Framework React
- **Mantine v7** - Biblioteca de componentes UI
- **TypeScript** - Tipagem estática
- **Zustand** - Gerenciamento de estado
- **Axios** - Cliente HTTP

### Infraestrutura
- **Docker & Docker Compose** - Containerização
- **Nginx** - Reverse proxy e servidor web
- **Let's Encrypt** - Certificados SSL gratuitos

## 📋 Funcionalidades

### ✅ Módulo de Cadastros
- **Colaboradores**: Gestão completa (nome, cargo, regime CLT/PJ, centro de custo)
- **Rubricas**: Tipos de pagamento (folha, benefícios, reembolsos) com configurações

### ✅ Módulo de Competência
- Criação de competências mensais por colaborador
- Clonagem automática de itens recorrentes do mês anterior
- Cálculo automático de totais (CLT, benefícios, geral)
- Fechamento de mês com bloqueio de edição
- Reabertura exclusiva para administradores

### ✅ Módulo de Pagamentos
- Lançamentos detalhados (data, valor, tipo, forma, status)
- **Limite de adiantamento**: 40% padrão, 50% com justificativa
- Controle de exceções
- Upload de comprovantes (MinIO/S3)
- Dashboard com totais e alertas

### ✅ Módulo de Relatórios
- Relatórios mensais consolidados
- Exportação em CSV e Excel
- Análise por colaborador
- Indicadores de pendências e exceções

### ✅ Segurança e Multi-tenant
- Autenticação JWT com refresh tokens
- RBAC: Admin, Financeiro, RH, Leitura
- Isolamento completo por tenant
- Auditoria de ações

### ✅ Anti "Encher Disco"
- **Arquivos**: MinIO para storage externo (não salva no banco)
- **Auditoria**: Particionamento por mês + retenção de 180 dias
- **Sessões**: Limpeza automática após 90 dias
- **Jobs diários**: Limpeza automática às 3h da manhã

## 📦 Instalação Rápida

### Pré-requisitos
- Docker e Docker Compose instalados
- Domínio apontado para o servidor (para SSL)

### 1. Clone ou baixe o projeto

```bash
cd /opt/financeiro-pro
```

### 2. Execute o script de deployment

```bash
chmod +x deploy.sh
./deploy.sh
```

O script irá:
1. ✅ Criar arquivo .env com SECRET_KEY aleatória
2. ✅ Buildar imagens Docker
3. ✅ Iniciar PostgreSQL e MinIO
4. ✅ Executar migrações do banco
5. ✅ Popular dados iniciais (seeds)
6. ✅ Iniciar todos os serviços

### 3. Obter certificado SSL (Produção)

```bash
# Edite o arquivo nginx/get-ssl.sh com seu email
chmod +x nginx/get-ssl.sh
./nginx/get-ssl.sh
```

## 🔐 Acesso ao Sistema

### URLs
- **Frontend**: https://contas.semppreonline.com.br
- **API Docs**: http://localhost:8002/docs (desenvolvimento)
- **MinIO Console**: http://localhost:9003

### Credenciais Padrão

**Admin**
- Email: `admin@financeiro.com`
- Senha: `admin123`

**Financeiro**
- Email: `financeiro@financeiro.com`
- Senha: `financeiro123`

**MinIO**
- User: `minioadmin`
- Password: `minioadmin123`

⚠️ **IMPORTANTE**: Altere todas as senhas em produção!

## 🗄️ Estrutura do Projeto

```
financeiro-pro/
├── backend/              # API FastAPI
│   ├── app/
│   │   ├── main.py      # Aplicação principal
│   │   ├── models.py    # Modelos SQLAlchemy
│   │   ├── schemas.py   # Schemas Pydantic
│   │   ├── auth.py      # Autenticação
│   │   ├── storage.py   # MinIO service
│   │   ├── jobs.py      # Jobs agendados
│   │   └── routers/     # Endpoints
│   ├── alembic/         # Migrations
│   ├── tests/           # Testes
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/            # Next.js App
│   ├── app/            # App Router
│   │   ├── login/      # Página de login
│   │   ├── dashboard/  # Dashboard principal
│   │   └── colaboradores/ # Gestão de colaboradores
│   ├── components/     # Componentes React
│   ├── lib/           # Utils e stores
│   ├── package.json
│   └── Dockerfile
│
├── nginx/              # Configuração Nginx
│   ├── nginx.conf
│   ├── conf.d/
│   │   └── financeiro.conf
│   └── get-ssl.sh
│
├── docker-compose.yml  # Orquestração completa
└── deploy.sh          # Script de deployment
```

## 🔧 Comandos Úteis

### Docker

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f [servico]
docker-compose logs -f api     # Logs da API
docker-compose logs -f web     # Logs do frontend

# Parar todos os serviços
docker-compose down

# Reiniciar um serviço
docker-compose restart api

# Reconstruir imagens
docker-compose build --no-cache
```

### Banco de Dados

```bash
# Criar nova migration
docker-compose run --rm api alembic revision --autogenerate -m "descricao"

# Executar migrations
docker-compose run --rm api alembic upgrade head

# Reverter migration
docker-compose run --rm api alembic downgrade -1

# Acessar PostgreSQL
docker-compose exec db psql -U financeiro -d financeiro_pro
```

### Backend

```bash
# Executar seeds novamente
docker-compose run --rm api python seeds.py

# Executar testes
docker-compose run --rm api pytest

# Limpeza manual de dados antigos
docker-compose exec api curl -X POST http://localhost:8000/maintenance/cleanup \
  -H "Authorization: Bearer YOUR_TOKEN"

# Acessar shell Python
docker-compose run --rm api python
```

### Frontend

```bash
# Acessar container
docker-compose exec web sh

# Instalar nova dependência (rebuild necessário)
cd frontend && npm install nova-dependencia
docker-compose build web
docker-compose up -d web
```

## 🗺️ Endpoints da API

### Autenticação
- `POST /auth/login` - Login
- `POST /auth/refresh` - Renovar token
- `GET /auth/me` - Dados do usuário
- `POST /auth/logout` - Logout

### Colaboradores
- `GET /employees` - Listar
- `POST /employees` - Criar
- `GET /employees/{id}` - Buscar
- `PUT /employees/{id}` - Atualizar
- `DELETE /employees/{id}` - Desativar

### Rubricas
- `GET /rubrics` - Listar
- `POST /rubrics` - Criar
- `PUT /rubrics/{id}` - Atualizar

### Competências
- `GET /competencies` - Listar
- `POST /competencies` - Criar
- `POST /competencies/{id}/clone-from-previous` - Clonar mês anterior
- `POST /competencies/{id}/close` - Fechar mês
- `POST /competencies/{id}/reopen` - Reabrir (admin)
- `GET /competencies/{id}/summary` - Resumo/Dashboard

### Itens da Competência
- `GET /competencies/{id}/items` - Listar
- `POST /competencies/{id}/items` - Adicionar
- `DELETE /competencies/{id}/items/{item_id}` - Remover

### Pagamentos
- `GET /payments?competency_id={id}` - Listar
- `POST /payments?competency_id={id}` - Criar
- `PUT /payments/{id}` - Atualizar
- `DELETE /payments/{id}` - Deletar

### Anexos
- `POST /attachments/presign` - Gerar URL de upload
- `POST /attachments/commit` - Confirmar upload
- `GET /attachments?entity_type=&entity_id=` - Listar
- `DELETE /attachments/{id}` - Deletar

### Relatórios
- `GET /reports/monthly?year=&month=` - Relatório mensal (JSON)
- `GET /reports/monthly.xlsx?year=&month=` - Exportar Excel
- `GET /reports/monthly.csv?year=&month=` - Exportar CSV

### Manutenção
- `POST /maintenance/cleanup` - Limpeza manual (admin)
- `GET /maintenance/stats` - Estatísticas do banco (admin)

## 🛡️ Segurança

### Roles e Permissões

| Role      | Colaboradores | Rubricas | Competências | Pagamentos | Relatórios | Manutenção |
|-----------|--------------|----------|--------------|------------|------------|------------|
| Admin     | ✅ Total     | ✅ Total | ✅ Total     | ✅ Total   | ✅ Total   | ✅ Total   |
| Financeiro| ✅ CUD       | ✅ CUD   | ✅ CUD       | ✅ CUD     | ✅ Read    | ❌         |
| RH        | ✅ CUD       | ❌ Read  | ✅ CUD       | ❌ Read    | ✅ Read    | ❌         |
| Leitura   | ✅ Read      | ✅ Read  | ✅ Read      | ✅ Read    | ✅ Read    | ❌         |

### Headers de Segurança (Nginx)
- HSTS (Strict-Transport-Security)
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection

## 📊 Modelo de Dados

### Principais Tabelas

**tenants** - Multi-tenant
- id, name, active, created_at

**users** - Usuários do sistema
- id, tenant_id, name, email, password_hash, role, active

**employees** - Colaboradores
- id, tenant_id, name, role_name, regime (CLT/PJ), cost_center, active

**rubrics** - Rubricas de pagamento
- id, tenant_id, name, category, entra_clt, entra_calculo_percentual, recurring, active

**competencies** - Competências mensais
- id, tenant_id, employee_id, year, month, status, base_percentual, totals_json, closed_at

**competency_items** - Itens da competência
- id, tenant_id, competency_id, rubric_id, value, notes

**payments** - Pagamentos
- id, tenant_id, competency_id, date, amount, kind, method, status, exception_reason

**attachments** - Metadados de arquivos
- id, tenant_id, entity_type, entity_id, key (MinIO), size, sha256, mime

**audit_log** - Auditoria (particionada por mês)
- id, tenant_id, user_id, action, entity_type, entity_id, changes, created_at

## 🔄 Retenção e Limpeza de Dados

### Política Implementada

| Tipo de Dado | Retenção | Limpeza |
|--------------|----------|---------|
| Audit Logs | 180 dias | Automática (diária) |
| Sessões/Tokens | 90 dias | Automática (diária) |
| Arquivos (MinIO) | Indefinida | Manual |
| Dados Financeiros | Permanente | ❌ Não apaga |

### Job de Limpeza
- **Quando**: Diariamente às 3h da manhã
- **O que faz**:
  - Remove logs de auditoria > 180 dias
  - Remove tokens expirados > 90 dias
  - Mantém dados contábeis intactos

## 🧪 Testes

```bash
# Executar todos os testes
docker-compose run --rm api pytest

# Testes com cobertura
docker-compose run --rm api pytest --cov=app

# Teste específico
docker-compose run --rm api pytest tests/test_main.py::test_login_success
```

## 🚀 Deployment em Produção

### Checklist

1. ✅ Alterar senhas padrão
2. ✅ Configurar SECRET_KEY forte
3. ✅ Obter certificado SSL
4. ✅ Configurar backup do PostgreSQL
5. ✅ Configurar backup do MinIO
6. ✅ Ajustar recursos do Docker (RAM, CPU)
7. ✅ Configurar monitoramento
8. ✅ Revisar logs de segurança

### Backup

```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U financeiro financeiro_pro > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U financeiro financeiro_pro < backup_20251213.sql

# Backup MinIO (usar mc - MinIO Client)
mc mirror local/minio/financeiro-attachments backup/minio/
```

## 🔍 Troubleshooting

### Problema: API não inicia
```bash
# Verificar logs
docker-compose logs api

# Verificar conexão com banco
docker-compose exec api python -c "from app.database import engine; print('OK')"
```

### Problema: Frontend não carrega
```bash
# Verificar variável de ambiente
docker-compose exec web env | grep NEXT_PUBLIC_API_URL

# Rebuild
docker-compose build web --no-cache
docker-compose up -d web
```

### Problema: SSL não funciona
```bash
# Verificar certificados
docker-compose exec nginx ls -la /etc/letsencrypt/live/

# Testar configuração Nginx
docker-compose exec nginx nginx -t

# Recarregar configuração
docker-compose restart nginx
```

## 📝 Próximos Passos / Roadmap

- [ ] Módulo Contas a Pagar
- [ ] Módulo Contas a Receber
- [ ] Integração bancária (OFX)
- [ ] Relatórios gráficos (Dashboard avançado)
- [ ] Notificações por email
- [ ] App mobile (React Native)
- [ ] Exportação PDF
- [ ] Conciliação bancária

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é privado e proprietário.

## 👥 Suporte

Para suporte, entre em contato com a equipe de desenvolvimento.

---

**Desenvolvido com ❤️ usando FastAPI, Next.js e as melhores práticas de engenharia de software.**
