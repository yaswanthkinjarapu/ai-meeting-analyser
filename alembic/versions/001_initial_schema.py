"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-18 01:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 2. meetings
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 3. media_files
    op.create_table(
        'media_files',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_extension', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 4. speakers
    op.create_table(
        'speakers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('speaker_label', sa.String(length=50), nullable=False),
        sa.Column('speaker_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 5. transcript_segments
    op.create_table(
        'transcript_segments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('speaker_id', sa.String(length=36), sa.ForeignKey('speakers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('speaker_name', sa.String(length=100), nullable=True),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 6. decisions
    op.create_table(
        'decisions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('decision_text', sa.Text(), nullable=False),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=False),
        sa.Column('review_status', sa.String(length=50), default='confirmed'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 7. action_items
    op.create_table(
        'action_items',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('responsible_person', sa.String(length=100), nullable=True),
        sa.Column('deadline', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('follow_up_status', sa.String(length=50), default='NOT_SCHEDULED'),
        sa.Column('normalized_deadline', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.String(length=20), default='medium'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 8. unresolved_questions
    op.create_table(
        'unresolved_questions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 9. meeting_summaries
    op.create_table(
        'meeting_summaries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('overview', sa.Text(), nullable=False),
        sa.Column('follow_up_plan', sa.Text(), nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('detailed_summary_json', sa.Text(), nullable=True),
        sa.Column('conversational_tone', sa.String(length=50), default='neutral'),
        sa.Column('tone_explanation', sa.Text(), nullable=True),
        sa.Column('meeting_outcome', sa.String(length=50), default='not_determined'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 10. topics
    op.create_table(
        'topics',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('importance', sa.String(length=20), default='medium'),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('segment_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 11. timeline_events
    op.create_table(
        'timeline_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_time_str', sa.String(length=50), nullable=False),
        sa.Column('timestamp_seconds', sa.Float(), nullable=False),
        sa.Column('event_title', sa.String(length=255), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=False),
        sa.Column('segment_id', sa.String(length=36), nullable=True),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 12. risks_blockers
    op.create_table(
        'risks_blockers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), default='medium'),
        sa.Column('status', sa.String(length=50), default='open'),
        sa.Column('mitigation', sa.Text(), nullable=True),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 13. dependencies
    op.create_table(
        'dependencies',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('prerequisite', sa.Text(), nullable=False),
        sa.Column('dependent_task', sa.Text(), nullable=False),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column('context_quote', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 14. follow_up_suggestions
    op.create_table(
        'follow_up_suggestions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('suggestion_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), default='general'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 15. live_meeting_sessions
    op.create_table(
        'live_meeting_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), default='IDLE'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('paused_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), default=0.0),
        sa.Column('audio_file_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 16. live_session_events
    op.create_table(
        'live_session_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('session_id', sa.String(length=36), sa.ForeignKey('live_meeting_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 17. calendar_events
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_item_id', sa.String(length=36), sa.ForeignKey('action_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(length=50), default='google'),
        sa.Column('external_event_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('timezone', sa.String(length=50), default='UTC'),
        sa.Column('status', sa.String(length=50), default='SCHEDULED'),
        sa.Column('evidence_quote', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 18. email_followups
    op.create_table(
        'email_followups',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_item_id', sa.String(length=36), sa.ForeignKey('action_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(length=50), default='gmail'),
        sa.Column('external_draft_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), default='DRAFT'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 19. follow_up_reminders
    op.create_table(
        'follow_up_reminders',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('meeting_id', sa.String(length=36), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_item_id', sa.String(length=36), sa.ForeignKey('action_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('question_id', sa.String(length=36), sa.ForeignKey('unresolved_questions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reminder_type', sa.String(length=50), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), default='PENDING'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # 20. user_integrations
    op.create_table(
        'user_integrations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('connected_account', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), default='connected'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # 21. user_settings
    op.create_table(
        'user_settings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('timezone', sa.String(length=50), default='Asia/Kolkata'),
        sa.Column('remind_24h_before', sa.Integer(), default=1),
        sa.Column('remind_when_overdue', sa.Integer(), default=1),
        sa.Column('remind_questions_days', sa.Integer(), default=3),
        sa.Column('auto_external_actions', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('user_settings')
    op.drop_table('user_integrations')
    op.drop_table('follow_up_reminders')
    op.drop_table('email_followups')
    op.drop_table('calendar_events')
    op.drop_table('live_session_events')
    op.drop_table('live_meeting_sessions')
    op.drop_table('follow_up_suggestions')
    op.drop_table('dependencies')
    op.drop_table('risks_blockers')
    op.drop_table('timeline_events')
    op.drop_table('topics')
    op.drop_table('meeting_summaries')
    op.drop_table('unresolved_questions')
    op.drop_table('action_items')
    op.drop_table('decisions')
    op.drop_table('transcript_segments')
    op.drop_table('speakers')
    op.drop_table('media_files')
    op.drop_table('meetings')
    op.drop_table('users')
