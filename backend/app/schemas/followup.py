from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.meeting import ActionItemResponse, UnresolvedQuestionResponse, RiskBlockerResponse, FollowUpSuggestionResponse

class CalendarEventCreateRequest(BaseModel):
    meeting_id: Optional[str] = None
    action_item_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    provider: str = "google"
    evidence_quote: Optional[str] = None

class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    meeting_id: Optional[str] = None
    action_item_id: Optional[str] = None
    provider: str
    external_event_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    timezone: str
    status: str
    evidence_quote: Optional[str] = None
    created_at: datetime

class EmailDraftCreateRequest(BaseModel):
    meeting_id: Optional[str] = None
    action_item_id: Optional[str] = None
    recipient: Optional[str] = None
    subject: str
    body: str
    provider: str = "gmail"

class EmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    meeting_id: Optional[str] = None
    action_item_id: Optional[str] = None
    recipient: Optional[str] = None
    subject: str
    body: str
    provider: str
    external_draft_id: Optional[str] = None
    status: str
    created_at: datetime

class FollowUpReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    meeting_id: Optional[str] = None
    action_item_id: Optional[str] = None
    question_id: Optional[str] = None
    reminder_type: str
    scheduled_for: datetime
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

class UserSettingsRequest(BaseModel):
    timezone: Optional[str] = None
    remind_24h_before: Optional[int] = None
    remind_when_overdue: Optional[int] = None
    remind_questions_days: Optional[int] = None

class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    timezone: str
    remind_24h_before: int
    remind_when_overdue: int
    remind_questions_days: int
    auto_external_actions: int

class UserIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    provider: str
    connected_account: Optional[str] = None
    status: str
    created_at: datetime

class FollowUpCenterResponse(BaseModel):
    overdue_actions: List[ActionItemResponse] = []
    due_soon_actions: List[ActionItemResponse] = []
    other_actions: List[ActionItemResponse] = []
    open_questions: List[UnresolvedQuestionResponse] = []
    risks_blockers: List[RiskBlockerResponse] = []
    suggestions: List[FollowUpSuggestionResponse] = []
    calendar_events: List[CalendarEventResponse] = []
    email_drafts: List[EmailDraftResponse] = []
    reminders: List[FollowUpReminderResponse] = []
    settings: UserSettingsResponse
    integrations: List[UserIntegrationResponse] = []
