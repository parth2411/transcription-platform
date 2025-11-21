"""add granola features tables

Revision ID: 003_add_granola_features
Revises: 002_add_diarization
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '003_add_granola_features'
down_revision = '002_add_diarization'
branch_labels = None
depends_on = None


def upgrade():
    # Create meeting_templates table first (referenced by calendar_connections)
    op.create_table(
        'meeting_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_template', sa.Boolean(), default=False),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('structure', sa.Text(), nullable=True),
        sa.Column('summary_prompt', sa.Text(), nullable=True),
        sa.Column('auto_extract_action_items', sa.Boolean(), default=True),
        sa.Column('auto_extract_decisions', sa.Boolean(), default=True),
        sa.Column('icon', sa.String(50), default='document'),
        sa.Column('color', sa.String(7), default='#3B82F6'),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create calendar_connections table
    op.create_table(
        'calendar_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('calendar_id', sa.String(255), nullable=False),
        sa.Column('calendar_name', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('sync_enabled', sa.Boolean(), default=True),
        sa.Column('auto_record_meetings', sa.Boolean(), default=False),
        sa.Column('default_template_id', UUID(as_uuid=True), sa.ForeignKey('meeting_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_token', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create meetings table
    op.create_table(
        'meetings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('calendar_connection_id', UUID(as_uuid=True), sa.ForeignKey('calendar_connections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('transcription_id', UUID(as_uuid=True), sa.ForeignKey('transcriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('template_id', UUID(as_uuid=True), sa.ForeignKey('meeting_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('calendar_event_id', sa.String(255), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('actual_start_time', sa.DateTime(), nullable=True),
        sa.Column('actual_end_time', sa.DateTime(), nullable=True),
        sa.Column('meeting_url', sa.Text(), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('participants', sa.Text(), nullable=True),
        sa.Column('organizer_email', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), default='scheduled'),
        sa.Column('recording_status', sa.String(50), default='not_started'),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_pattern', sa.Text(), nullable=True),
        sa.Column('parent_meeting_id', UUID(as_uuid=True), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_points', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create meeting_notes table
    op.create_table(
        'meeting_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('meeting_id', UUID(as_uuid=True), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('note_type', sa.String(20), nullable=False),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('timestamp_in_meeting', sa.Integer(), nullable=True),
        sa.Column('speaker', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create action_items table
    op.create_table(
        'action_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('meeting_id', UUID(as_uuid=True), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to_email', sa.String(255), nullable=True),
        sa.Column('assigned_to_name', sa.String(255), nullable=True),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_from_ai', sa.Boolean(), default=False),
        sa.Column('related_transcript_chunk', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create transcription_tags junction table
    op.create_table(
        'transcription_tags',
        sa.Column('transcription_id', UUID(as_uuid=True), sa.ForeignKey('transcriptions.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tag_id', UUID(as_uuid=True), sa.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # Create integrations table
    op.create_table(
        'integrations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('config', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create indexes for better query performance
    op.create_index('ix_calendar_connections_user_id', 'calendar_connections', ['user_id'])
    op.create_index('ix_meetings_user_id', 'meetings', ['user_id'])
    op.create_index('ix_meetings_start_time', 'meetings', ['start_time'])
    op.create_index('ix_meetings_status', 'meetings', ['status'])
    op.create_index('ix_meetings_calendar_event_id', 'meetings', ['calendar_event_id'])
    op.create_index('ix_meeting_notes_meeting_id', 'meeting_notes', ['meeting_id'])
    op.create_index('ix_action_items_meeting_id', 'action_items', ['meeting_id'])
    op.create_index('ix_action_items_user_id', 'action_items', ['user_id'])
    op.create_index('ix_action_items_status', 'action_items', ['status'])
    op.create_index('ix_action_items_assigned_to_email', 'action_items', ['assigned_to_email'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_action_items_assigned_to_email', 'action_items')
    op.drop_index('ix_action_items_status', 'action_items')
    op.drop_index('ix_action_items_user_id', 'action_items')
    op.drop_index('ix_action_items_meeting_id', 'action_items')
    op.drop_index('ix_meeting_notes_meeting_id', 'meeting_notes')
    op.drop_index('ix_meetings_calendar_event_id', 'meetings')
    op.drop_index('ix_meetings_status', 'meetings')
    op.drop_index('ix_meetings_start_time', 'meetings')
    op.drop_index('ix_meetings_user_id', 'meetings')
    op.drop_index('ix_calendar_connections_user_id', 'calendar_connections')

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('integrations')
    op.drop_table('transcription_tags')
    op.drop_table('action_items')
    op.drop_table('meeting_notes')
    op.drop_table('meetings')
    op.drop_table('calendar_connections')
    op.drop_table('meeting_templates')
