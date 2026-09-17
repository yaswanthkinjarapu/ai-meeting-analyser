import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import models
from app.core.config import settings
from app.services import ai_intelligence, transcription

def utc_now():
    return datetime.now(timezone.utc)

def create_live_session(title: str, user_id: str, db: Session) -> models.LiveMeetingSession:
    """Creates a new Meeting and associated LiveMeetingSession for an authenticated user."""
    meeting_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    meeting = models.Meeting(
        id=meeting_id,
        user_id=user_id,
        title=title or "Live Meeting",
        status="PROCESSING"
    )
    db.add(meeting)
    db.flush()

    # Define path for audio recording file
    uploads_dir = Path(settings.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    audio_path = uploads_dir / f"live_{session_id}.wav"

    # Create MediaFile entry
    media_file = models.MediaFile(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        filename=audio_path.name,
        file_type="audio",
        file_extension="wav",
        file_path=str(audio_path),
        file_size_bytes=0,
        duration_seconds=0.0,
        language="en"
    )
    db.add(media_file)

    session = models.LiveMeetingSession(
        id=session_id,
        meeting_id=meeting_id,
        user_id=user_id,
        status="RECORDING",
        started_at=utc_now(),
        audio_file_path=str(audio_path)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_live_session_or_404(
    session_id: str,
    db: Session,
    current_user: Optional[models.User] = None
) -> models.LiveMeetingSession:
    """Retrieves a LiveMeetingSession and verifies user ownership if current_user is provided."""
    session = db.query(models.LiveMeetingSession).filter(models.LiveMeetingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live meeting session '{session_id}' not found."
        )

    if current_user is not None and session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not own this live meeting session."
        )

    return session

def pause_live_session(
    session_id: str,
    db: Session,
    current_user: Optional[models.User] = None
) -> models.LiveMeetingSession:
    """Pauses an active live meeting session."""
    session = get_live_session_or_404(session_id, db, current_user)
    if session.status not in ["RECORDING", "STARTING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pause session in status '{session.status}'."
        )

    session.status = "PAUSED"
    session.paused_at = utc_now()
    db.commit()
    db.refresh(session)
    return session

def resume_live_session(
    session_id: str,
    db: Session,
    current_user: Optional[models.User] = None
) -> models.LiveMeetingSession:
    """Resumes a paused live meeting session."""
    session = get_live_session_or_404(session_id, db, current_user)
    if session.status != "PAUSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume session in status '{session.status}'."
        )

    session.status = "RECORDING"
    session.paused_at = None
    db.commit()
    db.refresh(session)
    return session

def process_live_transcript_chunk(
    session_id: str,
    text: str,
    speaker_label: Optional[str],
    start_time: Optional[float],
    end_time: Optional[float],
    db: Session
) -> Dict[str, Any]:
    """
    Processes a finalized transcript segment chunk during live meeting:
    1. Saves TranscriptSegment to database.
    2. Runs incremental intelligence extraction.
    3. Returns segment and current live intelligence payload.
    """
    session = db.query(models.LiveMeetingSession).filter(models.LiveMeetingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    meeting_id = session.meeting_id

    # Calculate timestamps if missing
    existing_count = db.query(models.TranscriptSegment).filter(models.TranscriptSegment.meeting_id == meeting_id).count()
    if start_time is None:
        start_time = float(existing_count * 15.0)
    if end_time is None:
        end_time = float(start_time + 10.0)

    # Save finalized segment
    seg = models.TranscriptSegment(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        speaker_label=speaker_label or "Speaker 1",
        start_time=start_time,
        end_time=end_time,
        text=text.strip()
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)

    # Incremental Intelligence Extraction & Deduplication
    all_segments = db.query(models.TranscriptSegment).filter(
        models.TranscriptSegment.meeting_id == meeting_id
    ).order_by(models.TranscriptSegment.start_time).all()

    intel_result = ai_intelligence.classify_and_extract_intelligence(all_segments)

    # Clear previous child entity records for clean incremental deduplication
    db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).delete()
    db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).delete()
    db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting_id).delete()
    db.query(models.MeetingTopic).filter(models.MeetingTopic.meeting_id == meeting_id).delete()
    db.query(models.ImportantMoment).filter(models.ImportantMoment.meeting_id == meeting_id).delete()
    db.query(models.MeetingRiskBlocker).filter(models.MeetingRiskBlocker.meeting_id == meeting_id).delete()
    db.query(models.TaskDependency).filter(models.TaskDependency.meeting_id == meeting_id).delete()
    db.query(models.TimelineEvent).filter(models.TimelineEvent.meeting_id == meeting_id).delete()
    db.query(models.FollowUpSuggestion).filter(models.FollowUpSuggestion.meeting_id == meeting_id).delete()

    # Persist updated incremental extractions
    db_decisions = [models.Decision(meeting_id=meeting_id, **d) for d in intel_result["decisions"]]
    db_actions = [models.ActionItem(meeting_id=meeting_id, **a) for a in intel_result["action_items"]]
    db_questions = [models.UnresolvedQuestion(meeting_id=meeting_id, **q) for q in intel_result["unresolved_questions"]]
    db_topics = [models.MeetingTopic(meeting_id=meeting_id, **t) for t in intel_result["topics"]]
    db_moments = [models.ImportantMoment(meeting_id=meeting_id, **m) for m in intel_result["important_moments"]]
    db_risks = [models.MeetingRiskBlocker(meeting_id=meeting_id, **r) for r in intel_result["risks_blockers"]]
    db_deps = [models.TaskDependency(meeting_id=meeting_id, **dep) for dep in intel_result["dependencies"]]
    db_timeline = [models.TimelineEvent(meeting_id=meeting_id, **te) for te in intel_result["timeline_events"]]
    db_suggs = [models.FollowUpSuggestion(meeting_id=meeting_id, **s) for s in intel_result["follow_up_suggestions"]]

    db.add_all(db_decisions + db_actions + db_questions + db_topics + db_moments + db_risks + db_deps + db_timeline + db_suggs)
    db.commit()

    return {
        "type": "transcript",
        "segment": {
            "id": seg.id,
            "meeting_id": seg.meeting_id,
            "speaker_label": seg.speaker_label,
            "speaker_name": seg.speaker_name,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text
        },
        "live_intelligence": intel_result
    }

def stop_live_session(
    session_id: str,
    db: Session,
    current_user: Optional[models.User] = None
) -> Dict[str, Any]:
    """
    Stops live meeting session:
    1. Updates session status to STOPPING -> PROCESSING -> COMPLETED.
    2. Runs full authoritative Phase 10 analysis.
    3. Updates meeting status to COMPLETED.
    """
    session = get_live_session_or_404(session_id, db, current_user)
    if session.status in ["COMPLETED", "FAILED", "CANCELLED"]:
        # If already completed, return existing analysis
        return ai_intelligence.get_meeting_analysis(session.meeting_id, db)

    session.status = "PROCESSING"
    session.ended_at = utc_now()
    if session.started_at:
        s_at = session.started_at.replace(tzinfo=None) if session.started_at.tzinfo else session.started_at
        e_at = session.ended_at.replace(tzinfo=None) if session.ended_at.tzinfo else session.ended_at
        session.duration_seconds = round((e_at - s_at).total_seconds(), 2)
    db.commit()

    meeting = db.query(models.Meeting).filter(models.Meeting.id == session.meeting_id).first()
    if meeting:
        meeting.status = "PROCESSING"
        db.commit()

    # Run authoritative Phase 10 meeting analysis
    try:
        ai_intelligence.process_meeting_analysis(session.meeting_id, db)
    except HTTPException as e:
        if e.status_code == 400 and "No transcript segments found" in str(e.detail):
            pass
        else:
            raise e

    session.status = "COMPLETED"
    if meeting:
        meeting.status = "COMPLETED"
    db.commit()

    return ai_intelligence.get_meeting_analysis(session.meeting_id, db)
