"""fiscal module - certificates, nfe documents and sync state

Revision ID: 010
Revises: 009
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela: company_certificates
    op.create_table(
        'company_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('cnpj', sa.String(20), nullable=False),
        sa.Column('cert_storage_key', sa.String(500), nullable=False),
        sa.Column('cert_password_enc', sa.Text(), nullable=False),
        sa.Column('cert_thumbprint', sa.String(200), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_to', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('company_id', name='uq_company_certificate')
    )
    op.create_index('idx_company_certificates_company', 'company_certificates', ['company_id'])
    op.create_index('idx_company_certificates_status', 'company_certificates', ['status'])
    
    # Tabela: sefaz_dfe_state
    op.create_table(
        'sefaz_dfe_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('last_nsu', sa.String(20), nullable=False, server_default='0'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(20), nullable=False, server_default='ok'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('company_id', name='uq_sefaz_state_company')
    )
    op.create_index('idx_sefaz_dfe_state_company', 'sefaz_dfe_state', ['company_id'])
    
    # Tabela: nfe_documents
    op.create_table(
        'nfe_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('chave', sa.String(44), nullable=False),
        sa.Column('nsu', sa.String(20), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),  # recebida, emitida, desconhecida
        sa.Column('situacao', sa.String(20), nullable=False, server_default='desconhecida'),  # autorizada, cancelada, denegada
        sa.Column('numero', sa.String(20), nullable=True),
        sa.Column('serie', sa.String(10), nullable=True),
        sa.Column('data_emissao', sa.DateTime(), nullable=True),
        sa.Column('cnpj_emitente', sa.String(20), nullable=True),
        sa.Column('emitente_nome', sa.String(200), nullable=True),
        sa.Column('cnpj_destinatario', sa.String(20), nullable=True),
        sa.Column('destinatario_nome', sa.String(200), nullable=True),
        sa.Column('valor_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('xml_storage_key', sa.String(500), nullable=False),
        sa.Column('xml_sha256', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('chave', name='uq_nfe_chave')
    )
    op.create_index('idx_nfe_documents_company', 'nfe_documents', ['company_id'])
    op.create_index('idx_nfe_documents_chave', 'nfe_documents', ['chave'])
    op.create_index('idx_nfe_documents_nsu', 'nfe_documents', ['nsu'])
    op.create_index('idx_nfe_documents_tipo', 'nfe_documents', ['tipo'])
    op.create_index('idx_nfe_documents_data_emissao', 'nfe_documents', ['data_emissao'])
    
    # Tabela: nfe_sync_logs (opcional, retenção 180 dias)
    op.create_table(
        'nfe_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('sync_type', sa.String(20), nullable=False),  # incremental, by_key, manual
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),  # success, error, partial
        sa.Column('docs_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('docs_imported', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE')
    )
    op.create_index('idx_nfe_sync_logs_company', 'nfe_sync_logs', ['company_id'])
    op.create_index('idx_nfe_sync_logs_started_at', 'nfe_sync_logs', ['started_at'])


def downgrade() -> None:
    op.drop_table('nfe_sync_logs')
    op.drop_table('nfe_documents')
    op.drop_table('sefaz_dfe_state')
    op.drop_table('company_certificates')
