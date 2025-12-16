"""Adiciona campos fiscais à tabela companies

Revision ID: 011
Revises: 010
Create Date: 2025-01-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona campos fiscais à tabela companies
    op.add_column('companies', sa.Column('ie', sa.String(20), nullable=True))
    op.add_column('companies', sa.Column('im', sa.String(20), nullable=True))
    op.add_column('companies', sa.Column('cep', sa.String(10), nullable=True))
    op.add_column('companies', sa.Column('logradouro', sa.String(200), nullable=True))
    op.add_column('companies', sa.Column('numero', sa.String(20), nullable=True))
    op.add_column('companies', sa.Column('complemento', sa.String(100), nullable=True))
    op.add_column('companies', sa.Column('bairro', sa.String(100), nullable=True))
    op.add_column('companies', sa.Column('cidade', sa.String(100), nullable=True))
    op.add_column('companies', sa.Column('uf', sa.String(2), nullable=True))
    op.add_column('companies', sa.Column('codigo_ibge_cidade', sa.String(10), nullable=True))
    op.add_column('companies', sa.Column('codigo_ibge_uf', sa.String(2), nullable=True))
    op.add_column('companies', sa.Column('regime_tributario', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'regime_tributario')
    op.drop_column('companies', 'codigo_ibge_uf')
    op.drop_column('companies', 'codigo_ibge_cidade')
    op.drop_column('companies', 'uf')
    op.drop_column('companies', 'cidade')
    op.drop_column('companies', 'bairro')
    op.drop_column('companies', 'complemento')
    op.drop_column('companies', 'numero')
    op.drop_column('companies', 'logradouro')
    op.drop_column('companies', 'cep')
    op.drop_column('companies', 'im')
    op.drop_column('companies', 'ie')
