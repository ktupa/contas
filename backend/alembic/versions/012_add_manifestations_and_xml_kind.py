"""
Add manifestacao table and xml_kind fields

Revision ID: 012
Revises: 011
Create Date: 2025-12-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('nfe_documents', sa.Column('xml_kind', sa.String(length=20), nullable=False, server_default='summary'))
    op.add_column('sefaz_dfe_state', sa.Column('last_cstat', sa.String(length=10), nullable=True))

    op.create_table(
        'nfe_manifestations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chave', sa.String(length=44), nullable=False),
        sa.Column('tp_evento', sa.String(length=10), nullable=False),
        sa.Column('dh_evento', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('protocolo', sa.String(length=100), nullable=True),
        sa.Column('tentativas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('company_id', 'chave', 'tp_evento', name='uq_manifestation_company_chave_tp'),
    )
    op.create_index('idx_manifest_company', 'nfe_manifestations', ['company_id'])
    op.create_index('idx_manifest_chave', 'nfe_manifestations', ['chave'])
    op.create_index('idx_manifest_status', 'nfe_manifestations', ['status'])


def downgrade() -> None:
    op.drop_index('idx_manifest_status', table_name='nfe_manifestations')
    op.drop_index('idx_manifest_chave', table_name='nfe_manifestations')
    op.drop_index('idx_manifest_company', table_name='nfe_manifestations')
    op.drop_table('nfe_manifestations')
    op.drop_column('sefaz_dfe_state', 'last_cstat')
    op.drop_column('nfe_documents', 'xml_kind')
