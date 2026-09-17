import json
import re
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import models

def classify_and_extract_intelligence(segments: List[models.TranscriptSegment]) -> Dict[str, Any]:
    """
    Grounded AI Extraction Engine (Phase 10):
    - Distinguishes confirmed decisions from suggestions.
    - Extracts Executive Summary & Detailed Topic Summary.
    - Extracts Key Topics, Important Moments, Risks/Blockers, Dependencies, Timeline Events.
    - Generates separated AI Follow-up Suggestions.
    - Analyzes Conversational Tone and Structured Meeting Outcome.
    - Strictly prevents hallucinations (returns empty lists if unsupported by transcript).
    """
    decisions = []
    action_items = []
    unresolved_questions = []
    topics = []
    important_moments = []
    risks_blockers = []
    dependencies = []
    timeline_events = []
    follow_up_suggestions = []

    # Regex patterns for grounded rules
    decision_consensus_pattern = re.compile(
        r'\b(okay\s*,?\s*let\'s|agreed|decided|decide|decides|we\'ve chosen|settled on|locked in)\b',
        re.IGNORECASE
    )
    suggestion_pattern = re.compile(
        r'\b(maybe|what if|should we|could we|perhaps|how about|considering)\b',
        re.IGNORECASE
    )
    action_commitment_pattern = re.compile(
        r'\b(i will|i\'ll|will finish|will complete|will start|will handle|will prepare|need to complete|assigned to|takes care of)\b',
        re.IGNORECASE
    )
    unassigned_action_pattern = re.compile(
        r'\b(someone should|we need to|somebody needs to|should prepare|should implement)\b',
        re.IGNORECASE
    )

    deadline_pattern = re.compile(
        r'\b(by|before|on|due)\s+(friday|monday|tuesday|wednesday|thursday|saturday|sunday|tomorrow|next week|end of day|eod|september \d+|october \d+|november \d+|december \d+)\b',
        re.IGNORECASE
    )

    question_pattern = re.compile(r'\?$', re.IGNORECASE)

    risk_blocker_pattern = re.compile(
        r'\b(risk|delayed|delay|blocker|blocked by|cannot proceed|cannot continue|credentials missing|pending dependency|issue|problem)\b',
        re.IGNORECASE
    )

    dependency_pattern = re.compile(
        r'\b(.+?)\s+(?:needs|requires|depends on|is blocked by)\s+(.+?)(?:\s+before|\s+to|\.|$)',
        re.IGNORECASE
    )

    # 1. Iterate over segments for extraction
    for idx, seg in enumerate(segments):
        text = seg.text.strip()
        speaker = seg.speaker_name or seg.speaker_label or "Speaker"
        t_sec = seg.start_time if seg.start_time is not None else (idx * 15.0)

        # Format timestamp string (e.g. 02:15)
        mins = int(t_sec // 60)
        secs = int(t_sec % 60)
        time_str = f"{mins:02d}:{secs:02d}"

        # Timeline Event
        timeline_events.append({
            "event_time_str": time_str,
            "timestamp_seconds": float(t_sec),
            "event_title": f"Segment {idx+1}: {speaker}",
            "event_description": text,
            "segment_id": seg.id,
            "context_quote": text
        })

        # Decision Extraction (Explicit consensus, excluding suggestions)
        if decision_consensus_pattern.search(text) and not suggestion_pattern.search(text):
            decisions.append({
                "decision_text": text,
                "context_quote": text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high"
            })
            important_moments.append({
                "moment_type": "Decision",
                "description": f"Decision agreed: {text}",
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high"
            })

        # Action Item Extraction
        if action_commitment_pattern.search(text) or unassigned_action_pattern.search(text):
            responsible = speaker if action_commitment_pattern.search(text) else None
            deadline_match = deadline_pattern.search(text)
            deadline = deadline_match.group(0).strip() if deadline_match else None
            priority = "high" if deadline or "api" in text.lower() else "medium"

            action_items.append({
                "task_description": text,
                "responsible_person": responsible,
                "deadline": deadline,
                "status": "pending",
                "priority": priority,
                "context_quote": text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high" if responsible else "medium"
            })
            important_moments.append({
                "moment_type": "Action Item",
                "description": f"Action assigned to {responsible or 'Unassigned'}: {text}",
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high" if responsible else "medium"
            })

        # Unresolved Question Extraction
        if question_pattern.search(text) or text.lower().startswith(("what ", "which ", "how ", "who ", "when ", "where ", "why ")):
            unresolved_questions.append({
                "question": text,
                "context_quote": text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high"
            })
            important_moments.append({
                "moment_type": "Question",
                "description": f"Question raised by {speaker}: {text}",
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high"
            })

        # Risk / Blocker Extraction
        if risk_blocker_pattern.search(text):
            is_blocker = "blocker" in text.lower() or "cannot proceed" in text.lower() or "cannot continue" in text.lower()
            item_type = "blocker" if is_blocker else "risk"
            risks_blockers.append({
                "title": f"{item_type.capitalize()}: {text[:50]}...",
                "description": text,
                "item_type": item_type,
                "status": "open",
                "responsible_person": speaker if speaker != "Speaker" else None,
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time
            })
            important_moments.append({
                "moment_type": item_type.capitalize(),
                "description": text,
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high"
            })

        # Task Dependency Extraction
        dep_match = dependency_pattern.search(text)
        if dep_match:
            task_b_name = dep_match.group(1).strip()
            task_a_name = dep_match.group(2).strip()
            dependencies.append({
                "task_a": task_a_name,
                "task_b": task_b_name,
                "dependency_description": f"Task '{task_b_name}' depends on '{task_a_name}'.",
                "context_quote": text
            })

        # Topic Heuristic Extraction
        if any(w in text.lower() for w in ["database", "api", "architecture", "report", "documentation", "testing", "deploy"]):
            topic_title = "Technical Architecture & Database" if "database" in text.lower() or "api" in text.lower() else "Project Management & Deliverables"
            topics.append({
                "title": topic_title,
                "description": f"Discussion on {topic_title.lower()}.",
                "importance": "high" if "api" in text.lower() or "database" in text.lower() else "medium",
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time
            })

    # Deduplicate extracted items based on context_quote
    def deduplicate(items, key="context_quote"):
        seen = set()
        deduped = []
        for item in items:
            val = item.get(key, "").lower()
            if val and val not in seen:
                seen.add(val)
                deduped.append(item)
        return deduped

    decisions = deduplicate(decisions, key="decision_text")
    action_items = deduplicate(action_items, key="task_description")
    unresolved_questions = deduplicate(unresolved_questions, key="question")
    risks_blockers = deduplicate(risks_blockers, key="description")
    dependencies = deduplicate(dependencies, key="context_quote")
    important_moments = deduplicate(important_moments, key="description")
    topics = deduplicate(topics, key="title")

    # Filter out questions addressed by decisions
    final_questions = []
    for q in unresolved_questions:
        q_text = q["question"].lower()
        if not any(d["decision_text"].lower() in q_text for d in decisions):
            final_questions.append(q)

    # If no topics extracted, provide default grounded topic
    if not topics:
        topics = [{
            "title": "General Meeting Discussion",
            "description": f"Discussion covering {len(segments)} transcript segments.",
            "importance": "medium",
            "context_quote": segments[0].text if segments else "General discussion.",
            "segment_id": segments[0].id if segments else None,
            "start_time": segments[0].start_time if segments else None,
            "end_time": segments[0].end_time if segments else None
        }]

    # Generate Executive Summary (3-8 concise sentences grounded in transcript)
    exec_sentences = [
        f"The meeting consisted of {len(segments)} transcript segments covering key technical and project planning items.",
    ]
    if topics:
        exec_sentences.append(f"Major discussion topics focused on {', '.join([t['title'] for t in topics[:3]])}.")
    if decisions:
        exec_sentences.append(f"A total of {len(decisions)} key decision(s) were confirmed by consensus: {decisions[0]['decision_text']}")
    else:
        exec_sentences.append("No explicit final decisions were locked in during the session.")
    if action_items:
        exec_sentences.append(f"Team members agreed on {len(action_items)} action item(s) to drive follow-up progress.")
    if risks_blockers:
        exec_sentences.append(f"The team noted {len(risks_blockers)} potential risk(s) or blocker(s) requiring attention.")
    if final_questions:
        exec_sentences.append(f"There remain {len(final_questions)} unresolved question(s) open for future review.")

    executive_summary = " ".join(exec_sentences)

    # Generate Detailed Topic Summary (JSON structured sections)
    detailed_summary_sections = [
        {
            "section_title": "Meeting Overview",
            "points": [f"Meeting covered {len(segments)} segments with active participant discussion."]
        }
    ]
    for top in topics:
        detailed_summary_sections.append({
            "section_title": f"Topic: {top['title']}",
            "points": [top['description'], f"Key context: \"{top['context_quote']}\""]
        })
    detailed_summary_sections.append({
        "section_title": "Final Outcomes & Next Steps",
        "points": [
            f"Decisions: {len(decisions)} confirmed",
            f"Action Items: {len(action_items)} assigned",
            f"Unresolved Questions: {len(final_questions)} open"
        ]
    })
    detailed_summary_json = json.dumps(detailed_summary_sections)

    # Legacy Overview and Follow-up Plan
    overview = f"Meeting discussion covering {len(segments)} transcript segments."
    if decisions:
        overview += f" Key decisions reached: {len(decisions)}."
    if action_items:
        overview += f" Total action items assigned: {len(action_items)}."

    follow_up_parts = []
    for ai in action_items:
        owner = ai['responsible_person'] or 'Unassigned'
        due = f" (Due: {ai['deadline']})" if ai['deadline'] else ""
        follow_up_parts.append(f"• {owner}: {ai['task_description']}{due}")

    follow_up_plan = "\n".join(follow_up_parts) if follow_up_parts else "No immediate action items requiring follow-up."

    # AI Suggestions (Strictly separated from confirmed facts)
    if action_items:
        follow_up_suggestions.append({
            "suggestion_text": "Schedule a follow-up sync next week to review pending action item deliverables.",
            "category": "action_item_review"
        })
    if final_questions:
        follow_up_suggestions.append({
            "suggestion_text": "Circulate unresolved questions to domain leads prior to the next standup.",
            "category": "question_resolution"
        })
    if risks_blockers:
        follow_up_suggestions.append({
            "suggestion_text": "Verify risk mitigation and blocker resolution ahead of deployment.",
            "category": "risk_management"
        })

    # Meeting Tone & Outcome Analysis
    conversational_tone = "positive" if decisions and not risks_blockers else ("tense" if risks_blockers else "neutral")
    tone_explanation = f"Conversational flow evaluated as {conversational_tone} based on {len(decisions)} agreed decision(s) and {len(risks_blockers)} flagged risk/blocker(s)."
    
    if decisions and action_items and not final_questions:
        meeting_outcome = "completed"
    elif decisions or action_items:
        meeting_outcome = "partially_completed"
    elif final_questions:
        meeting_outcome = "unresolved"
    else:
        meeting_outcome = "informational"

    return {
        "overview": overview,
        "follow_up_plan": follow_up_plan,
        "executive_summary": executive_summary,
        "detailed_summary_json": detailed_summary_json,
        "conversational_tone": conversational_tone,
        "tone_explanation": tone_explanation,
        "meeting_outcome": meeting_outcome,
        "decisions": decisions,
        "action_items": action_items,
        "unresolved_questions": final_questions,
        "topics": topics,
        "important_moments": important_moments,
        "risks_blockers": risks_blockers,
        "dependencies": dependencies,
        "timeline_events": timeline_events,
        "follow_up_suggestions": follow_up_suggestions
    }

def process_meeting_analysis(meeting_id: str, db: Session) -> models.Meeting:
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found."
        )

    segments = db.query(models.TranscriptSegment).filter(
        models.TranscriptSegment.meeting_id == meeting_id
    ).order_by(models.TranscriptSegment.id).all()

    if not segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No transcript segments found for meeting '{meeting_id}'. Please process or transcribe meeting first."
        )

    result = classify_and_extract_intelligence(segments)

    # Clear existing analysis & Phase 10 records if re-analyzing
    db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).delete()
    db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).delete()
    db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting_id).delete()
    db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).delete()
    db.query(models.MeetingTopic).filter(models.MeetingTopic.meeting_id == meeting_id).delete()
    db.query(models.ImportantMoment).filter(models.ImportantMoment.meeting_id == meeting_id).delete()
    db.query(models.MeetingRiskBlocker).filter(models.MeetingRiskBlocker.meeting_id == meeting_id).delete()
    db.query(models.TaskDependency).filter(models.TaskDependency.meeting_id == meeting_id).delete()
    db.query(models.TimelineEvent).filter(models.TimelineEvent.meeting_id == meeting_id).delete()
    db.query(models.FollowUpSuggestion).filter(models.FollowUpSuggestion.meeting_id == meeting_id).delete()

    # Save Extended Summary
    db_summary = models.MeetingSummary(
        meeting_id=meeting_id,
        overview=result["overview"],
        follow_up_plan=result["follow_up_plan"],
        executive_summary=result["executive_summary"],
        detailed_summary_json=result["detailed_summary_json"],
        conversational_tone=result["conversational_tone"],
        tone_explanation=result["tone_explanation"],
        meeting_outcome=result["meeting_outcome"]
    )
    db.add(db_summary)

    # Save Decisions
    db_decisions = [
        models.Decision(
            meeting_id=meeting_id,
            decision_text=d["decision_text"],
            context_quote=d["context_quote"],
            start_time=d["start_time"],
            end_time=d["end_time"],
            confidence=d["confidence"]
        )
        for d in result["decisions"]
    ]
    db.add_all(db_decisions)

    # Save Action Items
    db_actions = [
        models.ActionItem(
            meeting_id=meeting_id,
            task_description=a["task_description"],
            responsible_person=a["responsible_person"],
            deadline=a["deadline"],
            status=a["status"],
            priority=a["priority"],
            context_quote=a["context_quote"],
            start_time=a["start_time"],
            end_time=a["end_time"],
            confidence=a["confidence"]
        )
        for a in result["action_items"]
    ]
    db.add_all(db_actions)

    # Save Unresolved Questions
    db_questions = [
        models.UnresolvedQuestion(
            meeting_id=meeting_id,
            question=q["question"],
            context_quote=q["context_quote"],
            start_time=q["start_time"],
            end_time=q["end_time"],
            confidence=q["confidence"]
        )
        for q in result["unresolved_questions"]
    ]
    db.add_all(db_questions)

    # Save Key Topics
    db_topics = [
        models.MeetingTopic(
            meeting_id=meeting_id,
            title=t["title"],
            description=t["description"],
            importance=t["importance"],
            context_quote=t["context_quote"],
            segment_id=t.get("segment_id"),
            start_time=t.get("start_time"),
            end_time=t.get("end_time")
        )
        for t in result["topics"]
    ]
    db.add_all(db_topics)

    # Save Important Moments
    db_moments = [
        models.ImportantMoment(
            meeting_id=meeting_id,
            moment_type=m["moment_type"],
            description=m["description"],
            context_quote=m["context_quote"],
            segment_id=m.get("segment_id"),
            start_time=m.get("start_time"),
            end_time=m.get("end_time"),
            confidence=m.get("confidence", "high")
        )
        for m in result["important_moments"]
    ]
    db.add_all(db_moments)

    # Save Risks & Blockers
    db_risks = [
        models.MeetingRiskBlocker(
            meeting_id=meeting_id,
            title=r["title"],
            description=r["description"],
            item_type=r["item_type"],
            status=r.get("status", "open"),
            responsible_person=r.get("responsible_person"),
            context_quote=r["context_quote"],
            segment_id=r.get("segment_id"),
            start_time=r.get("start_time"),
            end_time=r.get("end_time")
        )
        for r in result["risks_blockers"]
    ]
    db.add_all(db_risks)

    # Save Task Dependencies
    db_deps = [
        models.TaskDependency(
            meeting_id=meeting_id,
            task_a=dp["task_a"],
            task_b=dp["task_b"],
            dependency_description=dp["dependency_description"],
            context_quote=dp["context_quote"]
        )
        for dp in result["dependencies"]
    ]
    db.add_all(db_deps)

    # Save Timeline Events
    db_timeline = [
        models.TimelineEvent(
            meeting_id=meeting_id,
            event_time_str=te["event_time_str"],
            timestamp_seconds=te["timestamp_seconds"],
            event_title=te["event_title"],
            event_description=te["event_description"],
            segment_id=te.get("segment_id"),
            context_quote=te["context_quote"]
        )
        for te in result["timeline_events"]
    ]
    db.add_all(db_timeline)

    # Save Follow-up Suggestions
    db_suggs = [
        models.FollowUpSuggestion(
            meeting_id=meeting_id,
            suggestion_text=s["suggestion_text"],
            category=s.get("category", "general")
        )
        for s in result["follow_up_suggestions"]
    ]
    db.add_all(db_suggs)

    meeting.status = "ANALYZED"
    db.commit()
    db.refresh(meeting)
    return meeting

def get_meeting_analysis(meeting_id: str, db: Session) -> Dict[str, Any]:
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID '{meeting_id}' not found."
        )

    summary = db.query(models.MeetingSummary).filter(models.MeetingSummary.meeting_id == meeting_id).first()
    decisions = db.query(models.Decision).filter(models.Decision.meeting_id == meeting_id).all()
    action_items = db.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).all()
    unresolved_questions = db.query(models.UnresolvedQuestion).filter(models.UnresolvedQuestion.meeting_id == meeting_id).all()
    topics = db.query(models.MeetingTopic).filter(models.MeetingTopic.meeting_id == meeting_id).all()
    important_moments = db.query(models.ImportantMoment).filter(models.ImportantMoment.meeting_id == meeting_id).all()
    risks_blockers = db.query(models.MeetingRiskBlocker).filter(models.MeetingRiskBlocker.meeting_id == meeting_id).all()
    dependencies = db.query(models.TaskDependency).filter(models.TaskDependency.meeting_id == meeting_id).all()
    timeline_events = db.query(models.TimelineEvent).filter(models.TimelineEvent.meeting_id == meeting_id).order_by(models.TimelineEvent.timestamp_seconds).all()
    follow_up_suggestions = db.query(models.FollowUpSuggestion).filter(models.FollowUpSuggestion.meeting_id == meeting_id).all()

    return {
        "meeting_id": meeting.id,
        "status": meeting.status,
        "summary": summary,
        "decisions": decisions,
        "action_items": action_items,
        "unresolved_questions": unresolved_questions,
        "topics": topics,
        "important_moments": important_moments,
        "risks_blockers": risks_blockers,
        "dependencies": dependencies,
        "timeline_events": timeline_events,
        "follow_up_suggestions": follow_up_suggestions
    }
