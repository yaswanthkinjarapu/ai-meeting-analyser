import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
from app.database import models
from app.schemas import meeting as schemas
from app.api.auth import get_current_user, get_optional_current_user
from app.core import security
from app.services import live_session_service

router = APIRouter(prefix="/live-meetings", tags=["Live Meetings"])

@router.post("", response_model=schemas.LiveSessionResponse, status_code=status.HTTP_201_CREATED)
def start_live_meeting(
    payload: schemas.LiveSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Starts a new Live Meeting Session.
    Mandatory authentication required. Session is strictly bound to the current user.
    """
    session = live_session_service.create_live_session(
        title=payload.title,
        user_id=current_user.id,
        db=db
    )
    return schemas.LiveSessionResponse(
        session_id=session.id,
        meeting_id=session.meeting_id,
        user_id=session.user_id,
        title=session.meeting.title,
        status=session.status,
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        error_message=session.error_message,
        created_at=session.created_at
    )

@router.get("/{session_id}", response_model=schemas.LiveSessionResponse)
def get_live_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves live session details with user ownership verification."""
    session = live_session_service.get_live_session_or_404(session_id, db, current_user)
    return schemas.LiveSessionResponse(
        session_id=session.id,
        meeting_id=session.meeting_id,
        user_id=session.user_id,
        title=session.meeting.title,
        status=session.status,
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        error_message=session.error_message,
        created_at=session.created_at
    )

@router.post("/{session_id}/pause", response_model=schemas.LiveSessionResponse)
def pause_live_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Pauses an ongoing live meeting session."""
    session = live_session_service.pause_live_session(session_id, db, current_user)
    return schemas.LiveSessionResponse(
        session_id=session.id,
        meeting_id=session.meeting_id,
        user_id=session.user_id,
        title=session.meeting.title,
        status=session.status,
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        error_message=session.error_message,
        created_at=session.created_at
    )

@router.post("/{session_id}/resume", response_model=schemas.LiveSessionResponse)
def resume_live_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Resumes a paused live meeting session."""
    session = live_session_service.resume_live_session(session_id, db, current_user)
    return schemas.LiveSessionResponse(
        session_id=session.id,
        meeting_id=session.meeting_id,
        user_id=session.user_id,
        title=session.meeting.title,
        status=session.status,
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
        duration_seconds=session.duration_seconds,
        error_message=session.error_message,
        created_at=session.created_at
    )

@router.post("/{session_id}/stop", response_model=schemas.MeetingAnalysisResponse)
def stop_live_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Stops live meeting session and returns final Phase 10 intelligence report."""
    try:
        return live_session_service.stop_live_session(session_id, db, current_user)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

@router.websocket("/{session_id}/stream")
async def live_meeting_stream(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket Endpoint for Real-time Live Meeting Audio Streaming & Transcript/Intelligence JSON updates.
    Validates token and user ownership before establishing connection.
    """
    # 1. Validate JWT Auth Token
    if not token:
        await websocket.close(code=4001, reason="Authentication token missing.")
        return

    payload = security.decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token.")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload.")
        return

    db = SessionLocal()
    try:
        # 2. Verify Session & User Ownership
        session = db.query(models.LiveMeetingSession).filter(models.LiveMeetingSession.id == session_id).first()
        if not session:
            await websocket.close(code=4004, reason="Live session not found.")
            return

        if session.user_id != user_id:
            await websocket.close(code=4003, reason="Forbidden: You do not own this live session.")
            return

        await websocket.accept()

        # Send initial status event
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "session_id": session_id,
            "session_status": session.status
        })

        while True:
            # Receive either text (JSON) or binary audio chunks
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                if session.audio_file_path:
                    p = Path(session.audio_file_path)
                    with open(p, "ab") as f:
                        f.write(audio_bytes)
                continue

            if "text" in message and message["text"]:
                raw_text = message["text"]
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON format."})
                    continue

                msg_type = data.get("type")

                if msg_type in ("ping", "heartbeat"):
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "partial_transcript":
                    # Broadcast partial transcript for live UI typing indicator
                    await websocket.send_json({
                        "type": "partial_transcript",
                        "text": data.get("text", ""),
                        "speaker": data.get("speaker", "Speaker 1")
                    })

                elif msg_type == "transcript":
                    text_content = data.get("text", "").strip()
                    if text_content:
                        speaker_lbl = data.get("speaker", "Speaker 1")
                        start_t = data.get("start_time")
                        end_t = data.get("end_time")

                        result = live_session_service.process_live_transcript_chunk(
                            session_id=session_id,
                            text=text_content,
                            speaker_label=speaker_lbl,
                            start_time=start_t,
                            end_time=end_t,
                            db=db
                        )
                        await websocket.send_json(result)

                elif msg_type == "pause":
                    session = live_session_service.pause_live_session(session_id, db)
                    await websocket.send_json({"type": "session_status", "status": session.status})

                elif msg_type == "resume":
                    session = live_session_service.resume_live_session(session_id, db)
                    await websocket.send_json({"type": "session_status", "status": session.status})

                elif msg_type == "stop":
                    final_analysis = live_session_service.stop_live_session(session_id, db)
                    await websocket.send_json({
                        "type": "final_report",
                        "status": "COMPLETED",
                        "analysis": final_analysis
                    })
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
