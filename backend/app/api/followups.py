import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database import models
from app.schemas import followup as schemas
from app.api.auth import get_current_user
from app.services import followup_service

router = APIRouter(tags=["Follow-ups & Calendar"])

# 1. Follow-up Center Endpoints
@router.get("/follow-ups", response_model=schemas.FollowUpCenterResponse)
def get_followup_center(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves complete Follow-Up Center dashboard data with strict user isolation."""
    return followup_service.get_followup_center_data(current_user.id, db)

@router.get("/follow-ups/upcoming")
def get_upcoming_followups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves upcoming action items and deadlines for the current user."""
    data = followup_service.get_followup_center_data(current_user.id, db)
    return {"upcoming": data["due_soon_actions"]}

@router.get("/follow-ups/overdue")
def get_overdue_followups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves overdue action items for the current user."""
    data = followup_service.get_followup_center_data(current_user.id, db)
    return {"overdue": data["overdue_actions"]}

@router.get("/follow-ups/suggestions")
def get_followup_suggestions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves AI follow-up suggestions with context evidence quotes for the current user."""
    data = followup_service.get_followup_center_data(current_user.id, db)
    return {"suggestions": data["suggestions"]}

@router.post("/follow-ups/{action_item_id}/schedule")
def prepare_schedule_followup(
    action_item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Prepares a calendar proposal for a specific action item with evidence quotes."""
    act = db.query(models.ActionItem).join(models.Meeting).filter(
        models.ActionItem.id == action_item_id,
        models.Meeting.user_id == current_user.id
    ).first()

    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_item_id}' not found or access denied."
        )

    return {
        "action_item_id": act.id,
        "meeting_id": act.meeting_id,
        "title": act.task_description,
        "responsible_person": act.responsible_person or "Not specified",
        "deadline": act.deadline or "Not specified",
        "evidence_quote": act.context_quote,
        "suggested_duration_minutes": 30
    }

# 2. Calendar Endpoints
@router.get("/calendar/status")
def get_calendar_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves connected calendar integration status for the current user."""
    integration = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "google_calendar"
    ).first()
    return {
        "connected": integration is not None and integration.status == "connected",
        "account": integration.connected_account if integration else None,
        "provider": "Google Calendar"
    }

@router.post("/calendar/connect")
def connect_calendar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Connects calendar integration for current user."""
    integration = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "google_calendar"
    ).first()

    if not integration:
        integration = models.UserIntegration(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider="google_calendar",
            connected_account=current_user.email,
            status="connected"
        )
        db.add(integration)
    else:
        integration.status = "connected"

    db.commit()
    db.refresh(integration)
    return {"message": "Google Calendar connected successfully.", "connected": True, "account": current_user.email}

@router.post("/calendar/disconnect")
def disconnect_calendar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Disconnects calendar integration for current user."""
    integration = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "google_calendar"
    ).first()

    if integration:
        integration.status = "disconnected"
        db.commit()

    return {"message": "Google Calendar disconnected.", "connected": False}

@router.get("/calendar/events", response_model=List[schemas.CalendarEventResponse])
def list_calendar_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lists scheduled calendar events for the current user."""
    return db.query(models.CalendarEvent).filter(
        models.CalendarEvent.user_id == current_user.id
    ).order_by(models.CalendarEvent.start_time).all()

@router.post("/calendar/events", response_model=schemas.CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    payload: schemas.CalendarEventCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a calendar event after explicit user confirmation."""
    return followup_service.create_calendar_event(
        user_id=current_user.id,
        data=payload.model_dump(),
        db=db
    )

@router.patch("/calendar/events/{event_id}", response_model=schemas.CalendarEventResponse)
def update_calendar_event(
    event_id: str,
    payload: schemas.CalendarEventCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Updates an existing calendar event."""
    event = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.id == event_id,
        models.CalendarEvent.user_id == current_user.id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found.")

    event.title = payload.title
    if payload.description:
        event.description = payload.description
    db.commit()
    db.refresh(event)
    return event

@router.delete("/calendar/events/{event_id}")
def delete_calendar_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Cancels/deletes a calendar event."""
    event = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.id == event_id,
        models.CalendarEvent.user_id == current_user.id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found.")

    db.delete(event)
    db.commit()
    return {"message": "Calendar event deleted successfully."}

# 3. Email Endpoints
@router.get("/email/drafts", response_model=List[schemas.EmailDraftResponse])
def list_email_drafts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lists email follow-up drafts for the current user."""
    return db.query(models.EmailFollowup).filter(
        models.EmailFollowup.user_id == current_user.id
    ).order_by(models.EmailFollowup.created_at.desc()).all()

@router.post("/email/drafts", response_model=schemas.EmailDraftResponse, status_code=status.HTTP_201_CREATED)
def create_email_draft(
    payload: schemas.EmailDraftCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates an email draft proposal for user review."""
    return followup_service.create_email_draft(
        user_id=current_user.id,
        data=payload.model_dump(),
        db=db
    )

@router.post("/email/send")
def send_email(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Sends an email draft after explicit user confirmation."""
    return followup_service.send_email_followup(
        user_id=current_user.id,
        draft_id=draft_id,
        db=db
    )

# 4. Reminders & Settings Endpoints
@router.get("/reminders", response_model=List[schemas.FollowUpReminderResponse])
def list_reminders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lists reminders for current user."""
    return db.query(models.FollowUpReminder).filter(
        models.FollowUpReminder.user_id == current_user.id
    ).order_by(models.FollowUpReminder.scheduled_for).all()

@router.patch("/reminders/{reminder_id}")
def update_reminder_status(
    reminder_id: str,
    status_val: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Updates reminder status (PENDING, SENT, CANCELLED)."""
    rem = db.query(models.FollowUpReminder).filter(
        models.FollowUpReminder.id == reminder_id,
        models.FollowUpReminder.user_id == current_user.id
    ).first()

    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found.")

    rem.status = status_val
    db.commit()
    db.refresh(rem)
    return rem

@router.get("/settings", response_model=schemas.UserSettingsResponse)
def get_user_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves settings and configured timezone for the current user."""
    return followup_service.get_user_settings(current_user.id, db)

@router.put("/settings", response_model=schemas.UserSettingsResponse)
def update_user_settings(
    payload: schemas.UserSettingsRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Updates user settings and timezone configuration."""
    stg = followup_service.get_user_settings(current_user.id, db)
    if payload.timezone is not None:
        stg.timezone = payload.timezone
    if payload.remind_24h_before is not None:
        stg.remind_24h_before = payload.remind_24h_before
    if payload.remind_when_overdue is not None:
        stg.remind_when_overdue = payload.remind_when_overdue
    if payload.remind_questions_days is not None:
        stg.remind_questions_days = payload.remind_questions_days

    db.commit()
    db.refresh(stg)
    return stg
