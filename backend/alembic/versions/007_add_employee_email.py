"""add employee email

Revision ID: 007
Revises: 006
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email column to employees table
    op.add_column('employees', sa.Column('email', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'email')
