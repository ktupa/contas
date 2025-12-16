-- Fix: Remover pagamentos de desconto duplicados
-- Criado em: 16/12/2025
-- 
-- PROBLEMA:
-- Pagamentos criados automaticamente com kind='desconto' causavam duplicação
-- porque os descontos já estão calculados nos itens da competência.
--
-- SOLUÇÃO:
-- 1. Deletar pagamentos kind='desconto' que foram criados automaticamente
-- 2. O frontend e backend agora filtram kind!='desconto' no cálculo de total_pago
--
-- BACKUP antes de executar:
-- pg_dump -U financeiro_user -h localhost -p 5432 financeiro_db > backup_before_fix.sql

BEGIN;

-- Ver quantos registros serão afetados
SELECT 
    COUNT(*) as total_descontos_automaticos,
    SUM(amount) as soma_valores
FROM payments
WHERE kind = 'desconto'
  AND description LIKE 'Desconto:%'
  AND status = 'pago';

-- Comentar a linha acima e descomentar abaixo para executar a limpeza:
-- DELETE FROM payments
-- WHERE kind = 'desconto'
--   AND description LIKE 'Desconto:%'
--   AND status = 'pago';

-- Verificar resultado
SELECT 
    c.id as competency_id,
    c.employee_id,
    c.month,
    c.year,
    (c.totals_json->>'total_geral')::float as liquido,
    COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'pago' AND p.kind != 'desconto'), 0) as total_pago_corrigido,
    (c.totals_json->>'total_geral')::float - COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'pago' AND p.kind != 'desconto'), 0) as saldo_correto
FROM competencies c
LEFT JOIN payments p ON p.competency_id = c.id
WHERE c.status = 'aberta'
GROUP BY c.id, c.employee_id, c.month, c.year, c.totals_json
ORDER BY c.year DESC, c.month DESC;

COMMIT;

-- Para executar via docker:
-- docker-compose exec db psql -U financeiro_user -d financeiro_db -f /tmp/fix-desconto-payments.sql
