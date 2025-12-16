"""
Migration para módulo de assinaturas eletrônicas (Documenso)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela principal de documentos para assinatura
    op.create_table(
        'signature_documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),  # competency, contract, etc
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), server_default='documenso', nullable=False),
        sa.Column('provider_doc_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='draft', nullable=False),
        
        # Timestamps do processo
        sa.Column('requested_at', sa.DateTime(), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('declined_at', sa.DateTime(), nullable=True),
        sa.Column('voided_at', sa.DateTime(), nullable=True),
        
        # Storage Keys (MinIO)
        sa.Column('original_storage_key', sa.String(), nullable=False),
        sa.Column('signed_storage_key', sa.String(), nullable=True),
        sa.Column('audit_storage_key', sa.String(), nullable=True),
        
        # Metadados dos arquivos
        sa.Column('original_sha256', sa.String(), nullable=True),
        sa.Column('signed_sha256', sa.String(), nullable=True),
        sa.Column('original_size', sa.Integer(), nullable=True),
        sa.Column('signed_size', sa.Integer(), nullable=True),
        
        # URLs externas (Documenso)
        sa.Column('sign_url', sa.String(), nullable=True),
        sa.Column('signed_view_url', sa.String(), nullable=True),
        
        # Auditoria interna
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_doc_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], )
    )
    
    # Índices para busca rápida
    op.create_index('idx_signatures_entity', 'signature_documents', ['tenant_id', 'entity_type', 'entity_id'])
    op.create_index('idx_signatures_status', 'signature_documents', ['tenant_id', 'status'])

    # Tabela de signatários
    op.create_table(
        'signature_signers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), server_default='signer', nullable=False), # signer, viewer
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('provider_signer_id', sa.String(), nullable=True),
        sa.Column('sign_url', sa.String(), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['signature_documents.id'], ondelete='CASCADE')
    )

    # Tabela de eventos (Webhooks/Logs)
    op.create_table(
        'signature_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['signature_documents.id'], ondelete='SET NULL')
    )


def downgrade() -> None:
    op.drop_table('signature_events')
    op.drop_table('signature_signers')
    op.drop_table('signature_documents')
