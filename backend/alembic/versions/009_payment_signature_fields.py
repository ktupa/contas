"""add payment signature fields

Revision ID: 009
Revises: 008
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add signature fields to payments table
    op.add_column('payments', sa.Column('signature_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('payments', sa.Column('signature_status', sa.String(50), nullable=True))
    op.add_column('payments', sa.Column('signature_url', sa.String(500), nullable=True))
    op.add_column('payments', sa.Column('signed_at', sa.DateTime(), nullable=True))
    
    # Add foreign key to signature_documents
    op.create_foreign_key(
        'fk_payments_signature_id',
        'payments',
        'signature_documents',
        ['signature_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_payments_signature_id', 'payments', type_='foreignkey')
    op.drop_column('payments', 'signed_at')
    op.drop_column('payments', 'signature_url')
    op.drop_column('payments', 'signature_status')
    op.drop_column('payments', 'signature_id')
