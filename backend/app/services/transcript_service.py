import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import models

def parse_txt_transcript(content: str) -> List[Dict[str, Any]]:
    """
    Parses TXT transcript content into segment dictionaries.
    Detects speaker labels (e.g. 'Harinath:', 'Speaker 1:') and timestamps ([00:01:23]).
    For unlabelled lines, speaker_label is None.
    """
    lines = content.splitlines()
    segments = []

    timestamp_range_pattern = re.compile(
        r'^[\[\(](\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]\s*(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]\s*(.*)$'
    )
    single_timestamp_pattern = re.compile(
        r'^[\[\(](\d{1,2}:\d{2}(?::\d{2})?)[\]\)]\s*(.*)$'
    )
    speaker_pattern = re.compile(
        r'^([A-Za-z0-9_\s\-\.]{1,40}):\s*(.*)$'
    )

    def parse_time_str(time_str: str) -> float:
        parts = time_str.split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return 0.0

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        start_time: Optional[float] = None
        end_time: Optional[float] = None
        speaker_label: Optional[str] = None
        text = line

        # 1. Timestamp range parsing
        range_match = timestamp_range_pattern.match(text)
        if range_match:
            start_time = parse_time_str(range_match.group(1))
            end_time = parse_time_str(range_match.group(2))
            text = range_match.group(3).strip()
        else:
            single_match = single_timestamp_pattern.match(text)
            if single_match:
                start_time = parse_time_str(single_match.group(1))
                text = single_match.group(2).strip()

        # 2. Speaker label parsing
        speaker_match = speaker_pattern.match(text)
        if speaker_match:
            candidate = speaker_match.group(1).strip()
            if candidate.lower() not in {"note", "warning", "http", "https", "important"}:
                speaker_label = candidate
                text = speaker_match.group(2).strip()

        if text:
            segments.append({
                "speaker_label": speaker_label,
                "start_time": start_time,
                "end_time": end_time,
                "text": text
            })

    return segments

def process_meeting_transcript(meeting_id: str, db: Session) -> models.Meeting:
    """
    Loads meeting and media file, processes TXT transcript, creates database segments,
    and updates meeting status (PROCESSING -> TRANSCRIBED or FAILED).
    Original file on disk is never overwritten.
    """
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found."
        )

    # Find the document/transcript file
    transcript_file = None
    for file_record in meeting.files:
        if file_record.file_type == "document" or file_record.file_extension == "txt":
            transcript_file = file_record
            break

    if not transcript_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No text transcript file found for meeting '{meeting_id}'."
        )

    file_path = Path(transcript_file.file_path)
    if not file_path.exists():
        meeting.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript file '{transcript_file.filename}' not found on disk."
        )

    # Set status to PROCESSING
    meeting.status = "PROCESSING"
    db.commit()

    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            meeting.status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcript file '{transcript_file.filename}' is empty."
            )

        parsed_segments = parse_txt_transcript(content)
        if not parsed_segments:
            meeting.status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No valid transcript text found in file '{transcript_file.filename}'."
            )

        # Clear any prior segments for re-processing
        db.query(models.TranscriptSegment).filter(
            models.TranscriptSegment.meeting_id == meeting_id
        ).delete()

        # Insert new transcript segments
        db_segments = [
            models.TranscriptSegment(
                meeting_id=meeting_id,
                speaker_label=seg["speaker_label"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"]
            )
            for seg in parsed_segments
        ]
        db.add_all(db_segments)

        meeting.status = "TRANSCRIBED"
        db.commit()
        db.refresh(meeting)
        return meeting

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        meeting.status = "FAILED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process transcript: {str(e)}"
        )
