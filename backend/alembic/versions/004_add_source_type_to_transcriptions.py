"""add source_type to transcriptions

Revision ID: 004_add_source_type
Revises: 003_add_granola_features
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_source_type'
down_revision = '003_add_granola_features'
branch_labels = None
depends_on = None


def upgrade():
    # Add source_type column to transcriptions table
    op.add_column('transcriptions', sa.Column('source_type', sa.String(20), server_default='upload'))

    # Create index for better query performance
    op.create_index('ix_transcriptions_source_type', 'transcriptions', ['source_type'])


def downgrade():
    # Drop index
    op.drop_index('ix_transcriptions_source_type', 'transcriptions')

    # Drop column
    op.drop_column('transcriptions', 'source_type')
