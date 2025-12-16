#!/bin/bash

# Script de backup automático

BACKUP_DIR="/backup/financeiro-pro"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "🔄 Iniciando backup em $DATE..."

# Backup PostgreSQL
echo "📦 Backup do PostgreSQL..."
docker-compose exec -T db pg_dump -U financeiro financeiro_pro | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup MinIO (opcional - pode ser grande)
# echo "📦 Backup do MinIO..."
# docker run --rm --volumes-from financeiro_minio -v $BACKUP_DIR:/backup alpine tar czf /backup/minio_$DATE.tar.gz /data

# Manter apenas últimos 7 backups
echo "🧹 Limpando backups antigos..."
ls -t $BACKUP_DIR/db_*.sql.gz | tail -n +8 | xargs rm -f 2>/dev/null

echo "✅ Backup concluído: $BACKUP_DIR/db_$DATE.sql.gz"
