"""Add calculation_type to rubrics and update defaults

Revision ID: 005
Revises: 004
Create Date: 2025-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add calculation_type column
    op.add_column('rubrics', sa.Column('calculation_type', sa.String(20), server_default='fixed', nullable=False))
    
    # Update defaults for entra_clt and entra_calculo_percentual to true
    op.execute("UPDATE rubrics SET entra_clt = true, entra_calculo_percentual = true WHERE entra_clt = false AND entra_calculo_percentual = false")


def downgrade() -> None:
    op.drop_column('rubrics', 'calculation_type')
