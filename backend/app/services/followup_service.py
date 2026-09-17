import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.database import models
from app.services.deadline_service import normalize_deadline
from app.services.providers.mock_calendar import MockCalendarProvider
from app.services.providers.mock_email import MockEmailProvider

def utc_now():
    return datetime.now(timezone.utc)

def get_user_settings(user_id: str, db: Session) -> models.UserSettings:
    """Retrieves or initializes user settings with default timezone 'Asia/Kolkata'."""
    settings_obj = db.query(models.UserSettings).filter(models.UserSettings.user_id == user_id).first()
    if not settings_obj:
        settings_obj = models.UserSettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            timezone="Asia/Kolkata",
            remind_24h_before=1,
            remind_when_overdue=1,
            remind_questions_days=3,
            auto_external_actions=0
        )
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)
    return settings_obj

def get_followup_center_data(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Aggregates centralized Follow-Up Center data for the authenticated user:
    - Overdue Action Items
    - Due Soon / Upcoming Action Items
    - Unresolved Questions
    - Risks & Blockers
    - AI Follow-up Suggestions with evidence
    - Scheduled Calendar Events
    - Email Drafts & Reminders
    """
    settings_obj = get_user_settings(user_id, db)
    now_utc = utc_now()

    # Query user meeting IDs
    user_meeting_ids = [m.id for m in db.query(models.Meeting.id).filter(models.Meeting.user_id == user_id).all()]

    # Query Action Items
    all_actions = db.query(models.ActionItem).filter(
        models.ActionItem.meeting_id.in_(user_meeting_ids)
    ).all() if user_meeting_ids else []

    overdue_actions = []
    due_soon_actions = []
    other_actions = []

    for act in all_actions:
        # Normalize deadline if not already done
        if act.deadline and not act.normalized_deadline:
            norm_dt, _ = normalize_deadline(act.deadline, base_date=now_utc, user_tz=settings_obj.timezone)
            if norm_dt:
                act.normalized_deadline = norm_dt
                db.commit()

        if act.status != "completed":
            if act.normalized_deadline:
                norm_dt = act.normalized_deadline
                if norm_dt.tzinfo is None:
                    norm_dt = norm_dt.replace(tzinfo=timezone.utc)
                if norm_dt < now_utc:
                    overdue_actions.append(act)
                else:
                    due_soon_actions.append(act)
            else:
                other_actions.append(act)

    # Query Unresolved Questions
    questions = db.query(models.UnresolvedQuestion).filter(
        models.UnresolvedQuestion.meeting_id.in_(user_meeting_ids),
        models.UnresolvedQuestion.status == "open"
    ).all() if user_meeting_ids else []

    # Query Risks & Blockers
    risks = db.query(models.MeetingRiskBlocker).filter(
        models.MeetingRiskBlocker.meeting_id.in_(user_meeting_ids),
        models.MeetingRiskBlocker.status == "open"
    ).all() if user_meeting_ids else []

    # Query Follow-up Suggestions
    suggestions = db.query(models.FollowUpSuggestion).filter(
        models.FollowUpSuggestion.meeting_id.in_(user_meeting_ids)
    ).all() if user_meeting_ids else []

    # Query Calendar Events
    calendar_events = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == user_id
    ).order_by(models.CalendarEvent.start_time).all()

    # Query Email Drafts
    email_drafts = db.query(models.EmailFollowup).filter(
        models.EmailFollowup.user_id == user_id
    ).order_by(models.EmailFollowup.created_at.desc()).all()

    # Query Reminders
    reminders = db.query(models.FollowUpReminder).filter(
        models.FollowUpReminder.user_id == user_id
    ).order_by(models.FollowUpReminder.scheduled_for).all()

    # Query Integrations Status
    integrations = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == user_id
    ).all()

    return {
        "overdue_actions": overdue_actions,
        "due_soon_actions": due_soon_actions,
        "other_actions": other_actions,
        "open_questions": questions,
        "risks_blockers": risks,
        "suggestions": suggestions,
        "calendar_events": calendar_events,
        "email_drafts": email_drafts,
        "reminders": reminders,
        "settings": settings_obj,
        "integrations": integrations
    }

def create_calendar_event(user_id: str, data: Dict[str, Any], db: Session) -> models.CalendarEvent:
    """Creates a calendar event after explicit user confirmation."""
    settings_obj = get_user_settings(user_id, db)
    provider = MockCalendarProvider()

    title = data.get("title", "Meeting Follow-up")
    start_str = data.get("start_time")
    end_str = data.get("end_time")

    if isinstance(start_str, str):
        start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    else:
        start_time = start_str or utc_now() + timedelta(days=1)

    if isinstance(end_str, str):
        end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    else:
        end_time = end_str or (start_time + timedelta(minutes=30))

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Invoke calendar provider
    ext_result = provider.create_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=data.get("description"),
        timezone=settings_obj.timezone
    )

    event = models.CalendarEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        meeting_id=data.get("meeting_id"),
        action_item_id=data.get("action_item_id"),
        provider=data.get("provider", "google"),
        external_event_id=ext_result.get("external_event_id"),
        title=title,
        description=data.get("description"),
        start_time=start_time,
        end_time=end_time,
        timezone=settings_obj.timezone,
        status="SCHEDULED",
        evidence_quote=data.get("evidence_quote")
    )
    db.add(event)

    # Update ActionItem follow_up_status if applicable
    if data.get("action_item_id"):
        act = db.query(models.ActionItem).filter(models.ActionItem.id == data["action_item_id"]).first()
        if act:
            act.follow_up_status = "SCHEDULED"

    db.commit()
    db.refresh(event)
    return event

def create_email_draft(user_id: str, data: Dict[str, Any], db: Session) -> models.EmailFollowup:
    """Creates an email draft proposal."""
    provider = MockEmailProvider()

    recipient = data.get("recipient") or "Not specified"
    subject = data.get("subject", "Meeting Follow-up")
    body = data.get("body", "")

    ext_result = provider.create_draft(recipient, subject, body)

    draft = models.EmailFollowup(
        id=str(uuid.uuid4()),
        user_id=user_id,
        meeting_id=data.get("meeting_id"),
        action_item_id=data.get("action_item_id"),
        recipient=recipient,
        subject=subject,
        body=body,
        provider=data.get("provider", "gmail"),
        external_draft_id=ext_result.get("external_draft_id"),
        status="DRAFT"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft

def send_email_followup(user_id: str, draft_id: str, db: Session) -> models.EmailFollowup:
    """Sends email draft after explicit user confirmation."""
    draft = db.query(models.EmailFollowup).filter(
        models.EmailFollowup.id == draft_id,
        models.EmailFollowup.user_id == user_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft '{draft_id}' not found."
        )

    if not draft.recipient or draft.recipient == "Not specified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send email: Recipient is not specified."
        )

    provider = MockEmailProvider()
    provider.send_email(draft.recipient, draft.subject, draft.body)

    draft.status = "SENT"
    db.commit()
    db.refresh(draft)
    return draft
