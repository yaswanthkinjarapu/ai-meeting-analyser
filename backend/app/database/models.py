import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(DateTime(timezone=True), default=utc_now, nullable=False) # or boolean
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meetings = relationship("Meeting", back_populates="user")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="UPLOADED", nullable=False)  # UPLOADED, QUEUED, PROCESSING, TRANSCRIBING, TRANSCRIBED, DIARIZED, ANALYZED, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="meetings")
    files = relationship("MediaFile", back_populates="meeting", cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.id")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan", order_by="Speaker.speaker_label")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    unresolved_questions = relationship("UnresolvedQuestion", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("MeetingSummary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    topics = relationship("MeetingTopic", back_populates="meeting", cascade="all, delete-orphan")
    important_moments = relationship("ImportantMoment", back_populates="meeting", cascade="all, delete-orphan")
    risks_blockers = relationship("MeetingRiskBlocker", back_populates="meeting", cascade="all, delete-orphan")
    dependencies = relationship("TaskDependency", back_populates="meeting", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="meeting", cascade="all, delete-orphan", order_by="TimelineEvent.timestamp_seconds")
    follow_up_suggestions = relationship("FollowUpSuggestion", back_populates="meeting", cascade="all, delete-orphan")
    live_sessions = relationship("LiveMeetingSession", back_populates="meeting", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="meeting", cascade="all, delete-orphan")
    email_followups = relationship("EmailFollowup", back_populates="meeting", cascade="all, delete-orphan")
    follow_up_reminders = relationship("FollowUpReminder", back_populates="meeting", cascade="all, delete-orphan")

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # document, audio, video
    file_extension = Column(String(10), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    language = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="files")

class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    speaker_label = Column(String(100), nullable=False)  # e.g. "Speaker 1", "Speaker 2", "Harinath"
    speaker_name = Column(String(100), nullable=True)    # User-mapped name e.g. "Harinath", null by default
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="speakers")
    transcript_segments = relationship("TranscriptSegment", back_populates="speaker_ref")

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    speaker_id = Column(String(36), ForeignKey("speakers.id"), nullable=True)
    speaker_label = Column(String(100), nullable=True)
    speaker_name = Column(String(100), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    text = Column(Text, nullable=False)

    meeting = relationship("Meeting", back_populates="transcript_segments")
    speaker_ref = relationship("Speaker", back_populates="transcript_segments")

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    decision_text = Column(Text, nullable=False)
    context_quote = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(String(20), default="high", nullable=False)  # high, medium, low
    review_status = Column(String(50), default="confirmed", nullable=False) # confirmed, needs_review, rejected
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="decisions")

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    task_description = Column(Text, nullable=False)
    responsible_person = Column(String(100), nullable=True)  # Name/Label or null if unassigned
    deadline = Column(String(100), nullable=True)            # Stated deadline or null if unmentioned
    status = Column(String(50), default="pending", nullable=False) # pending, in_progress, completed, cancelled
    follow_up_status = Column(String(50), default="NOT_SCHEDULED", nullable=False) # NOT_SCHEDULED, SUGGESTED, SCHEDULED, COMPLETED, CANCELLED
    normalized_deadline = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String(20), default="medium", nullable=False) # high, medium, low
    notes = Column(Text, nullable=True)                       # User editable notes
    context_quote = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(String(20), default="high", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="action_items")

class UnresolvedQuestion(Base):
    __tablename__ = "unresolved_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    question = Column(Text, nullable=False)
    context_quote = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(String(20), default="high", nullable=False)
    status = Column(String(50), default="open", nullable=False) # open, resolved, not_applicable
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="unresolved_questions")

class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    overview = Column(Text, nullable=False)
    follow_up_plan = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=True)
    detailed_summary_json = Column(Text, nullable=True)
    conversational_tone = Column(String(50), default="neutral", nullable=True)
    tone_explanation = Column(Text, nullable=True)
    meeting_outcome = Column(String(50), default="not_determined", nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="summary")

class MeetingTopic(Base):
    __tablename__ = "meeting_topics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    importance = Column(String(20), default="medium", nullable=False) # high, medium, low
    context_quote = Column(Text, nullable=False)
    segment_id = Column(String(36), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="topics")

class ImportantMoment(Base):
    __tablename__ = "important_moments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    moment_type = Column(String(50), nullable=False) # Decision, Action Item, Problem, Blocker, Milestone, etc.
    description = Column(Text, nullable=False)
    context_quote = Column(Text, nullable=False)
    segment_id = Column(String(36), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    confidence = Column(String(20), default="high", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="important_moments")

class MeetingRiskBlocker(Base):
    __tablename__ = "meeting_risks_blockers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    item_type = Column(String(20), nullable=False) # risk, blocker
    status = Column(String(50), default="open", nullable=False)
    responsible_person = Column(String(100), nullable=True)
    context_quote = Column(Text, nullable=False)
    segment_id = Column(String(36), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="risks_blockers")

class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    task_a = Column(String(255), nullable=False) # Prerequisite task
    task_b = Column(String(255), nullable=False) # Dependent task (Task B depends on Task A)
    dependency_description = Column(Text, nullable=False)
    context_quote = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="dependencies")

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    event_time_str = Column(String(50), nullable=False) # e.g. "02:14"
    timestamp_seconds = Column(Float, default=0.0, nullable=False)
    event_title = Column(String(255), nullable=False)
    event_description = Column(Text, nullable=False)
    segment_id = Column(String(36), nullable=True)
    context_quote = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="timeline_events")

class FollowUpSuggestion(Base):
    __tablename__ = "follow_up_suggestions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    suggestion_text = Column(Text, nullable=False)
    category = Column(String(50), default="general", nullable=False)
    is_suggestion = Column(DateTime, default=utc_now) # bool marker column, or integer/string
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    meeting = relationship("Meeting", back_populates="follow_up_suggestions")

class LiveMeetingSession(Base):
    __tablename__ = "live_meeting_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="RECORDING", nullable=False)  # IDLE, STARTING, RECORDING, PAUSED, STOPPING, PROCESSING, COMPLETED, FAILED, CANCELLED
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    audio_file_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")
    meeting = relationship("Meeting", back_populates="live_sessions")

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    action_item_id = Column(String(36), ForeignKey("action_items.id"), nullable=True)
    provider = Column(String(50), default="google", nullable=False)
    external_event_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    status = Column(String(50), default="SCHEDULED", nullable=False)
    evidence_quote = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")
    meeting = relationship("Meeting", back_populates="calendar_events")
    action_item = relationship("ActionItem")

class EmailFollowup(Base):
    __tablename__ = "email_followups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    action_item_id = Column(String(36), ForeignKey("action_items.id"), nullable=True)
    recipient = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    provider = Column(String(50), default="gmail", nullable=False)
    external_draft_id = Column(String(255), nullable=True)
    status = Column(String(50), default="DRAFT", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")
    meeting = relationship("Meeting", back_populates="email_followups")
    action_item = relationship("ActionItem")

class FollowUpReminder(Base):
    __tablename__ = "follow_up_reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    meeting_id = Column(String(36), ForeignKey("meetings.id"), nullable=True)
    action_item_id = Column(String(36), ForeignKey("action_items.id"), nullable=True)
    question_id = Column(String(36), ForeignKey("unresolved_questions.id"), nullable=True)
    reminder_type = Column(String(50), default="upcoming_deadline", nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")
    meeting = relationship("Meeting", back_populates="follow_up_reminders")
    action_item = relationship("ActionItem")

class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    connected_account = Column(String(255), nullable=True)
    status = Column(String(50), default="connected", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    remind_24h_before = Column(Integer, default=1, nullable=False)
    remind_when_overdue = Column(Integer, default=1, nullable=False)
    remind_questions_days = Column(Integer, default=3, nullable=False)
    auto_external_actions = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User")


