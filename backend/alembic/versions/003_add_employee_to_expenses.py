"""add_employee_to_expenses

Revision ID: 003
Revises: 002
Create Date: 2025-12-14 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add employee_id column to expenses table
    op.add_column('expenses', sa.Column('employee_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_expenses_employee', 'expenses', 'employees', ['employee_id'], ['id'])
    op.create_index('idx_expenses_employee', 'expenses', ['employee_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_expenses_employee', table_name='expenses')
    op.drop_constraint('fk_expenses_employee', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'employee_id')
