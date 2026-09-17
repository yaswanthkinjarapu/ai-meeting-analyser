import os
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.session import get_db
from app.database import models
from app.api.auth import get_optional_current_user
from app.schemas.meeting import (
    MeetingResponse,
    MeetingUploadResponse,
    MeetingTranscriptResponse,
    SpeakerResponse,
    SpeakerMapRequest,
    MeetingSpeakersResponse,
    MeetingAnalysisResponse,
    DecisionResponse,
    ActionItemResponse,
    UnresolvedQuestionResponse,
    ActionItemUpdateRequest,
    DecisionUpdateRequest,
    QuestionUpdateRequest,
    MeetingStatsResponse
)
from app.services import (
    file_service,
    transcript_service,
    transcription,
    video_processor,
    diarization,
    ai_intelligence
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])

def verify_meeting_access(
    meeting_id: str,
    db: Session,
    current_user: Optional[models.User]
) -> models.Meeting:
    """
    Enforces user data isolation and ownership protection:
    - Rejects access to non-existent meeting with 404.
    - If meeting is owned by a specific user, verifies current_user match.
    - Rejects unauthorized cross-user access with 403 Forbidden.
    """
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found."
        )

    if meeting.user_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access this user resource."
            )
        if current_user.id != meeting.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this meeting."
            )

    return meeting

def _enrich_meeting_counts(meeting: models.Meeting, db: Session) -> dict:
    """Helper to attach count metadata for decisions, action items, and questions."""
    dec_count = db.query(models.Decision).filter(models.Decision.meeting_id == meeting.id).count()
    act_count = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting.id).count()
    que_count = db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting.id).count()
    
    res = {
        "id": meeting.id,
        "user_id": meeting.user_id,
        "title": meeting.title,
        "status": meeting.status,
        "error_message": meeting.error_message,
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
        "files": meeting.files,
        "decisions_count": dec_count,
        "action_items_count": act_count,
        "unresolved_questions_count": que_count
    }
    return res

@router.get("/stats", response_model=MeetingStatsResponse)
def get_user_meeting_stats(
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves aggregated stats for meetings owned by the current user."""
    meeting_query = db.query(models.Meeting)
    if current_user:
        meeting_query = meeting_query.filter(
            (models.Meeting.user_id == current_user.id) | (models.Meeting.user_id.is_(None))
        )
    user_meetings = meeting_query.all()
    user_m_ids = [m.id for m in user_meetings]

    total_meetings = len(user_meetings)
    completed_meetings = sum(1 for m in user_meetings if m.status in ["TRANSCRIBED", "DIARIZED", "ANALYZED", "COMPLETED"])
    processing_meetings = sum(1 for m in user_meetings if m.status in ["QUEUED", "PROCESSING", "TRANSCRIBING", "DIARIZING", "ANALYZING"])
    failed_meetings = sum(1 for m in user_meetings if m.status == "FAILED")

    if user_m_ids:
        total_decisions = db.query(models.Decision).filter(models.Decision.meeting_id.in_(user_m_ids)).count()
        open_action_items = db.query(models.ActionItem).filter(
            models.ActionItem.meeting_id.in_(user_m_ids),
            models.ActionItem.status.in_(["pending", "in_progress"])
        ).count()
        completed_action_items = db.query(models.ActionItem).filter(
            models.ActionItem.meeting_id.in_(user_m_ids),
            models.ActionItem.status == "completed"
        ).count()
        open_questions = db.query(models.UnresolvedQuestion).filter(
            models.UnresolvedQuestion.meeting_id.in_(user_m_ids),
            models.UnresolvedQuestion.status == "open"
        ).count()
    else:
        total_decisions = 0
        open_action_items = 0
        completed_action_items = 0
        open_questions = 0

    return {
        "total_meetings": total_meetings,
        "completed_meetings": completed_meetings,
        "processing_meetings": processing_meetings,
        "failed_meetings": failed_meetings,
        "total_decisions": total_decisions,
        "open_action_items": open_action_items,
        "completed_action_items": completed_action_items,
        "open_questions": open_questions
    }

@router.get("/search", response_model=List[MeetingResponse])
def search_meetings(
    q: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """
    Search meetings by matching title, transcript text, decision text, action item text, question text, topic, or risk/blocker.
    Enforces strict user data isolation.
    """
    if not q or not q.strip():
        return []

    term = f"%{q.strip()}%"

    # Query meeting IDs matching query in any sub-entity
    m_ids_title = db.query(models.Meeting.id).filter(models.Meeting.title.ilike(term)).all()
    m_ids_trans = db.query(models.TranscriptSegment.meeting_id).filter(models.TranscriptSegment.text.ilike(term)).all()
    m_ids_dec = db.query(models.Decision.meeting_id).filter(models.Decision.decision_text.ilike(term)).all()
    m_ids_act = db.query(models.ActionItem.meeting_id).filter(models.ActionItem.task_description.ilike(term)).all()
    m_ids_que = db.query(models.UnresolvedQuestion.meeting_id).filter(models.UnresolvedQuestion.question.ilike(term)).all()
    m_ids_top = db.query(models.MeetingTopic.meeting_id).filter(models.MeetingTopic.title.ilike(term) | models.MeetingTopic.description.ilike(term)).all()
    m_ids_rsk = db.query(models.MeetingRiskBlocker.meeting_id).filter(models.MeetingRiskBlocker.title.ilike(term) | models.MeetingRiskBlocker.description.ilike(term)).all()
    m_ids_mom = db.query(models.ImportantMoment.meeting_id).filter(models.ImportantMoment.description.ilike(term)).all()

    matched_ids = set(
        [r[0] for r in m_ids_title] +
        [r[0] for r in m_ids_trans] +
        [r[0] for r in m_ids_dec] +
        [r[0] for r in m_ids_act] +
        [r[0] for r in m_ids_que] +
        [r[0] for r in m_ids_top] +
        [r[0] for r in m_ids_rsk] +
        [r[0] for r in m_ids_mom]
    )

    if not matched_ids:
        return []

    query = db.query(models.Meeting).filter(models.Meeting.id.in_(matched_ids))
    if current_user:
        query = query.filter(
            (models.Meeting.user_id == current_user.id) | (models.Meeting.user_id.is_(None))
        )
    
    meetings = query.all()
    return [_enrich_meeting_counts(m, db) for m in meetings]

@router.post("/upload", response_model=MeetingUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting(
    title: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """
    Upload a meeting file (.txt, .pdf, .docx, .mp3, .wav, .m4a, .flac, .ogg, .mp4, .mov, .mkv, .avi, .webm).
    Ensures safe filename generation, path traversal security, and user ownership binding.
    """
    if not title:
        title = file.filename or "Untitled Meeting"

    file_path, ext, size_bytes = await file_service.save_uploaded_file(file)
    category = file_service.get_file_category(ext)

    user_id = current_user.id if current_user else None
    db_meeting = models.Meeting(
        title=title,
        status="UPLOADED",
        user_id=user_id
    )
    db.add(db_meeting)
    db.flush()

    db_file = models.MediaFile(
        meeting_id=db_meeting.id,
        filename=file.filename or "unknown",
        file_type=category,
        file_extension=ext,
        file_path=file_path,
        file_size_bytes=size_bytes
    )
    db.add(db_file)
    db.commit()

    # Process pipeline with error handling
    try:
        if ext == "txt":
            db_meeting = transcript_service.process_meeting_transcript(db_meeting.id, db)
        elif category == "audio":
            db_meeting = transcription.process_audio_transcription(db_meeting.id, db)
        elif category == "video":
            db_meeting = video_processor.process_video_meeting(db_meeting.id, db)
        else:
            db.refresh(db_meeting)
    except Exception as e:
        db_meeting.status = "FAILED"
        db_meeting.error_message = str(e)
        db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meeting processing failed: {str(e)}"
        )

    message = "Meeting file uploaded successfully."
    if db_meeting.status == "TRANSCRIBED":
        if ext == "txt":
            message = "Meeting transcript uploaded and processed successfully."
        elif category == "audio":
            message = "Meeting audio uploaded and transcribed successfully."
        elif category == "video":
            message = "Meeting video uploaded, audio extracted, and transcribed successfully."

    return {
        "message": message,
        "meeting": _enrich_meeting_counts(db_meeting, db)
    }

@router.post("/{meeting_id}/analyze", response_model=MeetingAnalysisResponse)
def analyze_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Executes grounded AI intelligence extraction (Decisions, Action Items, Ownership, Deadlines, Questions, Summary)."""
    verify_meeting_access(meeting_id, db, current_user)
    try:
        ai_intelligence.process_meeting_analysis(meeting_id, db)
        return ai_intelligence.get_meeting_analysis(meeting_id, db)
    except Exception as e:
        m = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
        if m:
            m.status = "FAILED"
            m.error_message = str(e)
            db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{meeting_id}/analysis", response_model=MeetingAnalysisResponse)
def get_meeting_analysis(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves stored AI meeting intelligence analysis with user ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    return ai_intelligence.get_meeting_analysis(meeting_id, db)

@router.get("/{meeting_id}/intelligence", response_model=MeetingAnalysisResponse)
def get_meeting_intelligence(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves complete Phase 10 structured intelligence package with user ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    return ai_intelligence.get_meeting_analysis(meeting_id, db)

@router.get("/{meeting_id}/topics")
def get_meeting_topics(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves extracted key topics for a given meeting ID with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    topics = db.query(models.MeetingTopic).filter(models.MeetingTopic.meeting_id == meeting_id).all()
    return {"meeting_id": meeting_id, "topics": topics}

@router.get("/{meeting_id}/timeline")
def get_meeting_timeline(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves chronological intelligence timeline for a given meeting ID with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    timeline = db.query(models.TimelineEvent).filter(models.TimelineEvent.meeting_id == meeting_id).order_by(models.TimelineEvent.timestamp_seconds).all()
    return {"meeting_id": meeting_id, "timeline": timeline}

@router.get("/{meeting_id}/risks")
def get_meeting_risks(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves extracted risks and blockers for a given meeting ID with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    risks = db.query(models.MeetingRiskBlocker).filter(models.MeetingRiskBlocker.meeting_id == meeting_id).all()
    return {"meeting_id": meeting_id, "risks_blockers": risks}

@router.get("/{meeting_id}/dependencies")
def get_meeting_dependencies(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves extracted task dependencies for a given meeting ID with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    deps = db.query(models.TaskDependency).filter(models.TaskDependency.meeting_id == meeting_id).all()
    return {"meeting_id": meeting_id, "dependencies": deps}

@router.get("/{meeting_id}/follow-up")
def get_meeting_followup(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieves structured follow-up plan separating confirmed facts from AI suggestions with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    action_items = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).all()
    decisions = db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).all()
    questions = db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting_id).all()
    suggestions = db.query(models.FollowUpSuggestion).filter(models.FollowUpSuggestion.meeting_id == meeting_id).all()
    return {
        "meeting_id": meeting_id,
        "confirmed_facts": {
            "decisions": decisions,
            "action_items": action_items
        },
        "open_items": {
            "questions": questions
        },
        "ai_suggestions": suggestions
    }

@router.post("/{meeting_id}/diarize", response_model=MeetingTranscriptResponse)
def run_diarization(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Run speaker diarization on a meeting with user ownership verification."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    try:
        meeting = diarization.run_diarization_for_meeting(meeting_id, db)
        segments = db.query(models.TranscriptSegment).filter(
            models.TranscriptSegment.meeting_id == meeting_id
        ).all()
        return {
            "meeting_id": meeting.id,
            "status": meeting.status,
            "total_segments": len(segments),
            "segments": segments
        }
    except Exception as e:
        meeting.status = "FAILED"
        meeting.error_message = str(e)
        db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{meeting_id}/speakers", response_model=MeetingSpeakersResponse)
def get_meeting_speakers(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieve all detected speaker records for a given meeting ID with ownership isolation."""
    verify_meeting_access(meeting_id, db, current_user)
    speakers = diarization.get_meeting_speakers(meeting_id, db)
    return {
        "meeting_id": meeting_id,
        "speakers": speakers
    }

@router.put("/{meeting_id}/speakers/{speaker_id}", response_model=SpeakerResponse)
def map_speaker_name(
    meeting_id: str,
    speaker_id: str,
    body: SpeakerMapRequest,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Maps/updates a user-provided name for a speaker record with ownership verification."""
    verify_meeting_access(meeting_id, db, current_user)
    return diarization.map_speaker_name(meeting_id, speaker_id, body.speaker_name, db)

# Phase 9: Editable Action Items, Decisions, Questions
@router.patch("/{meeting_id}/action-items/{action_item_id}", response_model=ActionItemResponse)
def update_action_item(
    meeting_id: str,
    action_item_id: str,
    body: ActionItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Updates action item metadata while preserving original transcript evidence."""
    verify_meeting_access(meeting_id, db, current_user)
    item = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_item_id,
        models.ActionItem.meeting_id == meeting_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_item_id}' not found in meeting '{meeting_id}'."
        )

    if body.task_description is not None:
        item.task_description = body.task_description
    if body.responsible_person is not None:
        item.responsible_person = body.responsible_person if body.responsible_person.strip() else None
    if body.deadline is not None:
        item.deadline = body.deadline if body.deadline.strip() else None
    if body.status is not None:
        if body.status not in ["pending", "in_progress", "completed", "cancelled"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action item status.")
        item.status = body.status
    if body.priority is not None:
        item.priority = body.priority
    if body.notes is not None:
        item.notes = body.notes

    db.commit()
    db.refresh(item)
    return item

@router.patch("/{meeting_id}/decisions/{decision_id}", response_model=DecisionResponse)
def update_decision(
    meeting_id: str,
    decision_id: str,
    body: DecisionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Updates decision review status (confirmed, needs_review, rejected) while preserving original transcript evidence."""
    verify_meeting_access(meeting_id, db, current_user)
    decision = db.query(models.Decision).filter(
        models.Decision.id == decision_id,
        models.Decision.meeting_id == meeting_id
    ).first()

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' not found in meeting '{meeting_id}'."
        )

    if body.review_status not in ["confirmed", "needs_review", "rejected"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid decision review status.")

    decision.review_status = body.review_status
    db.commit()
    db.refresh(decision)
    return decision

@router.patch("/{meeting_id}/questions/{question_id}", response_model=UnresolvedQuestionResponse)
def update_unresolved_question(
    meeting_id: str,
    question_id: str,
    body: QuestionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Updates unresolved question status (open, resolved, not_applicable) while preserving original transcript evidence."""
    verify_meeting_access(meeting_id, db, current_user)
    question = db.query(models.UnresolvedQuestion).filter(
        models.UnresolvedQuestion.id == question_id,
        models.UnresolvedQuestion.meeting_id == meeting_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found in meeting '{meeting_id}'."
        )

    if body.status not in ["open", "resolved", "not_applicable"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid question status.")

    question.status = body.status
    db.commit()
    db.refresh(question)
    return question

# Phase 9 & 10: Report Export (Markdown / JSON)
@router.get("/{meeting_id}/export")
def export_meeting_report(
    meeting_id: str,
    format: str = "markdown",
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Generates a downloadable meeting intelligence report in Markdown (.md) or JSON format."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    summary = db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).first()
    decisions = db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).all()
    action_items = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).all()
    questions = db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting_id).all()
    topics = db.query(models.MeetingTopic).filter(models.MeetingTopic.meeting_id == meeting_id).all()
    important_moments = db.query(models.ImportantMoment).filter(models.ImportantMoment.meeting_id == meeting_id).all()
    risks_blockers = db.query(models.MeetingRiskBlocker).filter(models.MeetingRiskBlocker.meeting_id == meeting_id).all()
    dependencies = db.query(models.TaskDependency).filter(models.TaskDependency.meeting_id == meeting_id).all()
    timeline_events = db.query(models.TimelineEvent).filter(models.TimelineEvent.meeting_id == meeting_id).order_by(models.TimelineEvent.timestamp_seconds).all()
    follow_up_suggestions = db.query(models.FollowUpSuggestion).filter(models.FollowUpSuggestion.meeting_id == meeting_id).all()

    fmt = format.lower()
    if fmt == "json":
        report_data = {
            "meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "status": meeting.status,
                "created_at": meeting.created_at.isoformat()
            },
            "summary": {
                "executive_summary": summary.executive_summary if summary and summary.executive_summary else (summary.overview if summary else "Not specified"),
                "overview": summary.overview if summary else "Not specified",
                "follow_up_plan": summary.follow_up_plan if summary else "Not specified",
                "conversational_tone": summary.conversational_tone if summary else "neutral",
                "meeting_outcome": summary.meeting_outcome if summary else "not_determined"
            },
            "topics": [
                {
                    "title": t.title,
                    "description": t.description,
                    "importance": t.importance,
                    "evidence": t.context_quote
                }
                for t in topics
            ],
            "decisions": [
                {
                    "decision": d.decision_text,
                    "review_status": d.review_status,
                    "evidence": d.context_quote
                }
                for d in decisions
            ],
            "action_items": [
                {
                    "task": a.task_description,
                    "responsible_person": a.responsible_person or "Not identified",
                    "deadline": a.deadline or "Not specified",
                    "status": a.status,
                    "evidence": a.context_quote
                }
                for a in action_items
            ],
            "unresolved_questions": [
                {
                    "question": q.question,
                    "status": q.status,
                    "evidence": q.context_quote
                }
                for q in questions
            ],
            "risks_and_blockers": [
                {
                    "title": r.title,
                    "type": r.item_type,
                    "description": r.description,
                    "evidence": r.context_quote
                }
                for r in risks_blockers
            ],
            "task_dependencies": [
                {
                    "task_a": dp.task_a,
                    "task_b": dp.task_b,
                    "description": dp.dependency_description,
                    "evidence": dp.context_quote
                }
                for dp in dependencies
            ],
            "timeline": [
                {
                    "time": te.event_time_str,
                    "title": te.event_title,
                    "description": te.event_description,
                    "evidence": te.context_quote
                }
                for te in timeline_events
            ],
            "ai_suggestions": [
                {
                    "suggestion": s.suggestion_text,
                    "category": s.category
                }
                for s in follow_up_suggestions
            ]
        }
        return Response(
            content=json.dumps(report_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="meeting_report_{meeting_id}.json"'}
        )
    else:
        # Default: Markdown export
        exec_sum = summary.executive_summary if summary and summary.executive_summary else (summary.overview if summary else "Not specified")
        lines = [
            f"# Meeting Intelligence Report: {meeting.title}",
            f"**Date**: {meeting.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Status**: {meeting.status}",
            f"**Conversational Tone**: {summary.conversational_tone if summary else 'neutral'}",
            f"**Meeting Outcome**: {summary.meeting_outcome if summary else 'not_determined'}",
            "",
            "## Executive Summary",
            exec_sum,
            ""
        ]

        if topics:
            lines.append("## Key Discussion Topics")
            for t in topics:
                lines.append(f"- **{t.title}** [`{t.importance.upper()}`]")
                lines.append(f"  {t.description}")
                lines.append(f"  *Evidence*: \"{t.context_quote}\"")
            lines.append("")

        lines.append("## Key Decisions")
        if decisions:
            for d in decisions:
                lines.append(f"- **{d.decision_text}** (Review Status: `{d.review_status}`)  ")
                lines.append(f"  *Evidence*: \"{d.context_quote}\"")
        else:
            lines.append("None identified.")

        lines.extend(["", "## Action Items"])
        if action_items:
            for a in action_items:
                resp = a.responsible_person or "Not identified"
                dl = a.deadline or "Not specified"
                lines.append(f"- [{a.status.upper()}] **{a.task_description}**")
                lines.append(f"  - **Responsible**: {resp} | **Deadline**: {dl} | **Priority**: {a.priority}")
                lines.append(f"  - *Evidence*: \"{a.context_quote}\"")
        else:
            lines.append("None identified.")

        lines.extend(["", "## Unresolved Questions"])
        if questions:
            for q in questions:
                lines.append(f"- **{q.question}** (Status: `{q.status}`)")
                lines.append(f"  *Evidence*: \"{q.context_quote}\"")
        else:
            lines.append("None identified.")

        if risks_blockers:
            lines.extend(["", "## Risks & Blockers"])
            for r in risks_blockers:
                lines.append(f"- [{r.item_type.upper()}] **{r.title}**")
                lines.append(f"  *Evidence*: \"{r.context_quote}\"")

        if dependencies:
            lines.extend(["", "## Task Dependencies"])
            for dp in dependencies:
                lines.append(f"- **{dp.task_b}** depends on **{dp.task_a}**")
                lines.append(f"  *Evidence*: \"{dp.context_quote}\"")

        if timeline_events:
            lines.extend(["", "## Chronological Timeline"])
            for te in timeline_events:
                lines.append(f"- `{te.event_time_str}` **{te.event_title}**: {te.event_description}")

        if follow_up_suggestions:
            lines.extend(["", "## AI Follow-up Suggestions (AI Generated)"])
            for s in follow_up_suggestions:
                lines.append(f"- *Suggestion*: {s.suggestion_text} [`{s.category}`]")

        md_content = "\n".join(lines)
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="meeting_report_{meeting_id}.md"'}
        )

# Phase 9: Safe Meeting Deletion
@router.delete("/{meeting_id}", status_code=status.HTTP_200_OK)
def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Deletes a meeting, associated database entities, and physical media files safely with ownership verification."""
    meeting = verify_meeting_access(meeting_id, db, current_user)

    # Delete physical media files from disk
    for file_rec in meeting.files:
        if file_rec.file_path:
            p = Path(file_rec.file_path)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                except Exception:
                    pass

    # Delete meeting entity (cascades to media_files, segments, speakers, decisions, actions, questions, summary)
    db.delete(meeting)
    db.commit()

    return {"message": f"Meeting '{meeting_id}' and associated files deleted successfully."}

@router.post("/{meeting_id}/process-video", response_model=MeetingTranscriptResponse)
def process_video(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Extracts audio from video and transcribes it via Whisper with ownership verification."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    try:
        meeting = video_processor.process_video_meeting(meeting_id, db)
        segments = db.query(models.TranscriptSegment).filter(
            models.TranscriptSegment.meeting_id == meeting_id
        ).all()
        return {
            "meeting_id": meeting.id,
            "status": meeting.status,
            "total_segments": len(segments),
            "segments": segments
        }
    except Exception as e:
        meeting.status = "FAILED"
        meeting.error_message = str(e)
        db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{meeting_id}/transcribe", response_model=MeetingTranscriptResponse)
def transcribe_audio(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Triggers audio speech-to-text transcription with ownership verification."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    try:
        meeting = transcription.process_audio_transcription(meeting_id, db)
        segments = db.query(models.TranscriptSegment).filter(
            models.TranscriptSegment.meeting_id == meeting_id
        ).all()
        return {
            "meeting_id": meeting.id,
            "status": meeting.status,
            "total_segments": len(segments),
            "segments": segments
        }
    except Exception as e:
        meeting.status = "FAILED"
        meeting.error_message = str(e)
        db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{meeting_id}/process-transcript", response_model=MeetingTranscriptResponse)
def process_transcript(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Triggers or re-runs transcript segment extraction for a text meeting file with ownership verification."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    try:
        meeting = transcript_service.process_meeting_transcript(meeting_id, db)
        segments = db.query(models.TranscriptSegment).filter(
            models.TranscriptSegment.meeting_id == meeting_id
        ).all()
        return {
            "meeting_id": meeting.id,
            "status": meeting.status,
            "total_segments": len(segments),
            "segments": segments
        }
    except Exception as e:
        meeting.status = "FAILED"
        meeting.error_message = str(e)
        db.commit()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[MeetingResponse])
def list_meetings(
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """List meetings with user data isolation: if authenticated, returns only user's meetings."""
    if current_user:
        query = db.query(models.Meeting).filter(
            (models.Meeting.user_id == current_user.id) | (models.Meeting.user_id.is_(None))
        )
    else:
        query = db.query(models.Meeting)

    meetings = query.order_by(models.Meeting.created_at.desc()).all()
    return [_enrich_meeting_counts(m, db) for m in meetings]

@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Get meeting details by ID with ownership isolation."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    return _enrich_meeting_counts(meeting, db)

@router.get("/{meeting_id}/transcript", response_model=MeetingTranscriptResponse)
def get_meeting_transcript(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user)
):
    """Retrieve stored transcript segments for a given meeting ID with ownership isolation."""
    meeting = verify_meeting_access(meeting_id, db, current_user)
    segments = db.query(models.TranscriptSegment).filter(
        models.TranscriptSegment.meeting_id == meeting_id
    ).all()

    return {
        "meeting_id": meeting.id,
        "status": meeting.status,
        "total_segments": len(segments),
        "segments": segments
    }
