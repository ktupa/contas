-- Script para corrigir sequências desincronizadas no PostgreSQL
-- Atualiza todas as sequências para o próximo valor disponível

-- Companies
SELECT setval('companies_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM companies), false);

-- Employees
SELECT setval('employees_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM employees), false);

-- Rubrics
SELECT setval('rubrics_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM rubrics), false);

-- Competencies
SELECT setval('competencies_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM competencies), false);

-- Payments
SELECT setval('payments_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM payments), false);

-- Attachments
SELECT setval('attachments_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM attachments), false);

-- Expenses
SELECT setval('expenses_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM expenses), false);

-- Users
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM users), false);

-- Tenants
SELECT setval('tenants_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM tenants), false);

SELECT 'Sequências corrigidas com sucesso!' as status;
