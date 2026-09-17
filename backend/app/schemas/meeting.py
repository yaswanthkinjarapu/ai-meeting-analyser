from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class MediaFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    file_extension: str
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    created_at: datetime

class SpeakerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    speaker_label: str
    speaker_name: Optional[str] = None
    created_at: datetime

class SpeakerMapRequest(BaseModel):
    speaker_name: str

class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    speaker_id: Optional[str] = None
    speaker_label: Optional[str] = None
    speaker_name: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: str

class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    title: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    files: List[MediaFileResponse] = []
    decisions_count: Optional[int] = 0
    action_items_count: Optional[int] = 0
    unresolved_questions_count: Optional[int] = 0

class MeetingUploadResponse(BaseModel):
    message: str
    meeting: MeetingResponse

class MeetingTranscriptResponse(BaseModel):
    meeting_id: str
    status: str
    total_segments: int
    segments: List[TranscriptSegmentResponse]

class MeetingSpeakersResponse(BaseModel):
    meeting_id: str
    speakers: List[SpeakerResponse]

# Phase 7 & 9 AI Intelligence Schemas
class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    decision_text: str
    context_quote: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: str
    review_status: str = "confirmed"
    created_at: datetime
    updated_at: Optional[datetime] = None

class ActionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    task_description: str
    responsible_person: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "pending"
    follow_up_status: str = "NOT_SCHEDULED"
    normalized_deadline: Optional[datetime] = None
    priority: str = "medium"
    notes: Optional[str] = None
    context_quote: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class UnresolvedQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    question: str
    context_quote: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: str
    status: str = "open"
    created_at: datetime
    updated_at: Optional[datetime] = None

class MeetingSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    overview: str
    follow_up_plan: str
    executive_summary: Optional[str] = None
    detailed_summary_json: Optional[str] = None
    conversational_tone: Optional[str] = "neutral"
    tone_explanation: Optional[str] = None
    meeting_outcome: Optional[str] = "not_determined"
    created_at: datetime

class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    title: str
    description: str
    importance: str = "medium"
    context_quote: str
    segment_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    created_at: datetime

class ImportantMomentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    moment_type: str
    description: str
    context_quote: str
    segment_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: str = "high"
    created_at: datetime

class RiskBlockerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    title: str
    description: str
    item_type: str  # risk, blocker
    status: str = "open"
    responsible_person: Optional[str] = None
    context_quote: str
    segment_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    created_at: datetime

class TaskDependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    task_a: str
    task_b: str
    dependency_description: str
    context_quote: str
    created_at: datetime

class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    event_time_str: str
    timestamp_seconds: float = 0.0
    event_title: str
    event_description: str
    segment_id: Optional[str] = None
    context_quote: str
    created_at: datetime

class FollowUpSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    suggestion_text: str
    category: str = "general"
    created_at: datetime

class MeetingAnalysisResponse(BaseModel):
    meeting_id: str
    status: str
    summary: Optional[MeetingSummaryResponse] = None
    decisions: List[DecisionResponse] = []
    action_items: List[ActionItemResponse] = []
    unresolved_questions: List[UnresolvedQuestionResponse] = []
    topics: List[TopicResponse] = []
    important_moments: List[ImportantMomentResponse] = []
    risks_blockers: List[RiskBlockerResponse] = []
    dependencies: List[TaskDependencyResponse] = []
    timeline_events: List[TimelineEventResponse] = []
    follow_up_suggestions: List[FollowUpSuggestionResponse] = []

class MeetingIntelligenceResponse(MeetingAnalysisResponse):
    pass

# Phase 9 Update Request Schemas
class ActionItemUpdateRequest(BaseModel):
    task_description: Optional[str] = None
    responsible_person: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None

class DecisionUpdateRequest(BaseModel):
    review_status: str  # confirmed, needs_review, rejected

class QuestionUpdateRequest(BaseModel):
    status: str  # open, resolved, not_applicable

class MeetingStatsResponse(BaseModel):
    total_meetings: int
    completed_meetings: int
    processing_meetings: int
    failed_meetings: int
    total_decisions: int
    open_action_items: int
    completed_action_items: int
    open_questions: int

# Phase 11 Live Meeting Schemas
class LiveSessionCreateRequest(BaseModel):
    title: str = "Live Meeting"

class LiveSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    meeting_id: str
    user_id: str
    title: str
    status: str
    started_at: datetime
    paused_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime

class LiveSessionControlRequest(BaseModel):
    action: str  # pause, resume, stop

