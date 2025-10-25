"""add diarization fields

Revision ID: 002_add_diarization
Revises: da5f520624fe
Create Date: 2025-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_diarization'
down_revision = 'da5f520624fe'
branch_labels = None
depends_on = None


def upgrade():
    # Add diarization_data column
    op.add_column('transcriptions', sa.Column('diarization_data', sa.Text(), nullable=True))

    # Add speaker_count column
    op.add_column('transcriptions', sa.Column('speaker_count', sa.Integer(), nullable=True))


def downgrade():
    # Remove diarization_data column
    op.drop_column('transcriptions', 'diarization_data')

    # Remove speaker_count column
    op.drop_column('transcriptions', 'speaker_count')
