"""004_restructure_company_system

Revision ID: 004
Revises: 003
Create Date: 2025-12-14 22:00:00.000000

Reestrutura o sistema:
- Renomeia suppliers para companies
- Adiciona campos à companies (address, is_main)
- Adiciona company_id, cpf, base_salary ao employees
- Atualiza expenses para usar company_id
- Adiciona campos due_date, paid_date, notes ao expenses
"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Criar tabela companies (nova estrutura)
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('cnpj', sa.String(20), nullable=True),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('is_main', sa.Boolean(), default=False, nullable=False),
        sa.Column('active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_companies_tenant', 'companies', ['tenant_id'])

    # 2. Migrar dados de suppliers para companies (se existirem)
    op.execute("""
        INSERT INTO companies (id, tenant_id, name, cnpj, email, phone, address, is_main, active, created_at)
        SELECT id, tenant_id, name, cnpj, email, phone, NULL, FALSE, active, created_at
        FROM suppliers
    """)

    # 3. Adicionar novos campos ao employees
    op.add_column('employees', sa.Column('cpf', sa.String(14), nullable=True))
    op.add_column('employees', sa.Column('base_salary', sa.Numeric(12, 2), nullable=True))
    op.add_column('employees', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_employees_company', 'employees', 'companies', ['company_id'], ['id'])
    op.create_index('idx_employees_company', 'employees', ['company_id'])

    # 4. Adicionar novos campos ao expenses
    op.add_column('expenses', sa.Column('due_date', sa.DateTime(), nullable=True))
    op.add_column('expenses', sa.Column('paid_date', sa.DateTime(), nullable=True))
    op.add_column('expenses', sa.Column('notes', sa.Text(), nullable=True))
    
    # 5. Adicionar company_id ao expenses e migrar de supplier_id
    op.add_column('expenses', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_expenses_company', 'expenses', 'companies', ['company_id'], ['id'])
    op.create_index('idx_expenses_company', 'expenses', ['company_id'])
    
    # Migrar supplier_id para company_id
    op.execute("UPDATE expenses SET company_id = supplier_id WHERE supplier_id IS NOT NULL")
    
    # 6. Remover supplier_id do expenses (comentado para manter compatibilidade)
    # op.drop_constraint('expenses_supplier_id_fkey', 'expenses', type_='foreignkey')
    # op.drop_column('expenses', 'supplier_id')


def downgrade() -> None:
    # Reverter na ordem inversa
    op.drop_index('idx_expenses_company', table_name='expenses')
    op.drop_constraint('fk_expenses_company', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'company_id')
    op.drop_column('expenses', 'notes')
    op.drop_column('expenses', 'paid_date')
    op.drop_column('expenses', 'due_date')
    
    op.drop_index('idx_employees_company', table_name='employees')
    op.drop_constraint('fk_employees_company', 'employees', type_='foreignkey')
    op.drop_column('employees', 'company_id')
    op.drop_column('employees', 'base_salary')
    op.drop_column('employees', 'cpf')
    
    op.drop_index('idx_companies_tenant', table_name='companies')
    op.drop_table('companies')
