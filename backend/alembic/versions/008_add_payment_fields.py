"""add payment description and rubrica_name fields

Revision ID: 008
Revises: 007
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Add description column to payments
    op.add_column('payments', sa.Column('description', sa.Text(), nullable=True))
    
    # Add rubrica_name column to payments
    op.add_column('payments', sa.Column('rubrica_name', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('payments', 'rubrica_name')
    op.drop_column('payments', 'description')
