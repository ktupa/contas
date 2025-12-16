# Financeiro Pro - Makefile para comandos comuns

.PHONY: help dev prod logs stop clean backup test

help: ## Mostra este help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Inicia ambiente de desenvolvimento
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Ambiente de desenvolvimento iniciado"
	@echo "API: http://localhost:8000/docs"
	@echo "MinIO: http://localhost:9001"

prod: ## Deploy em produção
	./deploy.sh

logs: ## Ver logs de todos os serviços
	docker-compose logs -f

logs-api: ## Ver logs apenas da API
	docker-compose logs -f api

logs-web: ## Ver logs apenas do frontend
	docker-compose logs -f web

stop: ## Para todos os containers
	docker-compose down

clean: ## Remove todos os containers e volumes (CUIDADO!)
	docker-compose down -v
	@echo "⚠️  Todos os dados foram removidos!"

backup: ## Executa backup do banco
	./scripts/backup.sh

migrate: ## Executa migrações do banco
	docker-compose run --rm api alembic upgrade head

seed: ## Popula dados iniciais
	docker-compose run --rm api python seeds.py

test: ## Executa testes
	docker-compose run --rm api pytest

shell-api: ## Acessa shell Python da API
	docker-compose exec api python

shell-db: ## Acessa PostgreSQL
	docker-compose exec db psql -U financeiro -d financeiro_pro

fix-sequences: ## Corrige sequências desincronizadas do banco
	docker-compose exec -T db psql -U financeiro -d financeiro_pro < scripts/fix-sequences.sql

stats: ## Mostra estatísticas dos containers
	docker stats

ssl: ## Obtém certificado SSL
	./nginx/get-ssl.sh

rebuild: ## Rebuild das imagens
	docker-compose build --no-cache
	docker-compose up -d

restart: ## Reinicia todos os serviços
	docker-compose restart

ps: ## Lista containers rodando
	docker-compose ps
