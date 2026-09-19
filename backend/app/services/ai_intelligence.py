import json
import re
from typing import List, Dict, Any, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import models


# ============================================================================
# GROUNDED EXTRACTION PATTERNS
# ============================================================================

# ---------------------------------------------------------------------------
# DECISIONS
# ---------------------------------------------------------------------------
#
# Confirmed decisions:
#
#   "Okay, let's use PostgreSQL."
#   "We will use PostgreSQL."
#   "We decided to use PostgreSQL."
#   "We officially decide to proceed with AWS."
#   "Decision: We officially decide to proceed with AWS."
#
# NOT confirmed:
#
#   "Maybe we should use PostgreSQL."
#   "We should use PostgreSQL."
#   "Could we use PostgreSQL?"
#
# The important rule is:
# discussion/suggestion != confirmed decision.
# ---------------------------------------------------------------------------

DECISION_PATTERN = re.compile(
    r"\b("
    r"okay\s*,?\s*let'?s|"
    r"agreed|"
    r"we\s+will\s+use|"
    r"we\s+will\s+(?:proceed|go\s+with|move\s+forward)|"
    r"we'?ve\s+chosen|"
    r"settled\s+on|"
    r"locked\s+in|"
    r"final\s+decision|"
    r"decided\s+(?:to|on)|"
    r"decide\s+(?:to|on)"
    r")\b",
    re.IGNORECASE,
)


EXPLICIT_DECISION_PREFIX_PATTERN = re.compile(
    r"^\s*(?:decision|final\s+decision)\s*:\s*(.+)$",
    re.IGNORECASE,
)


SUGGESTION_PATTERN = re.compile(
    r"\b("
    r"maybe|"
    r"perhaps|"
    r"what\s+if|"
    r"should\s+we|"
    r"could\s+we|"
    r"how\s+about|"
    r"might|"
    r"consider"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# DIRECT ACTION COMMITMENTS
# ---------------------------------------------------------------------------

DIRECT_ACTION_PATTERN = re.compile(
    r"\b("
    r"i\s+will|"
    r"i'?ll|"
    r"will\s+(?:"
    r"finish|"
    r"complete|"
    r"start|"
    r"handle|"
    r"prepare|"
    r"create|"
    r"update|"
    r"review|"
    r"access|"
    r"check|"
    r"send|"
    r"submit|"
    r"implement|"
    r"fix|"
    r"test|"
    r"deploy|"
    r"document|"
    r"write|"
    r"build|"
    r"configure|"
    r"verify|"
    r"confirm"
    r")|"
    r"assigned\s+to|"
    r"takes?\s+care\s+of"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# NAMED-PERSON ACTION
#
# Example:
#
#   Bob will complete the Terraform configuration by Friday.
#
# Only speaker names already present in transcript metadata are accepted.
# This prevents the extractor from inventing people.
# ---------------------------------------------------------------------------

NAMED_ACTION_PATTERN = re.compile(
    r"^\s*(?P<person>.+?)\s+"
    r"(?:will|shall|is\s+going\s+to)\s+"
    r"(?P<task>.+?)\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# ACTIONS WITHOUT IDENTIFIED RESPONSIBLE PERSON
# ---------------------------------------------------------------------------

UNASSIGNED_ACTION_PATTERN = re.compile(
    r"\b("
    r"someone\s+should|"
    r"somebody\s+should|"
    r"someone\s+needs\s+to|"
    r"somebody\s+needs\s+to|"
    r"we\s+need\s+to|"
    r"should\s+prepare|"
    r"should\s+implement|"
    r"need\s+to\s+complete"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# EXPLICIT ACTION-ITEM PREFIX
# ---------------------------------------------------------------------------

EXPLICIT_ACTION_PREFIX_PATTERN = re.compile(
    r"^\s*(?:action\s+item|action|task)\s*:\s*(.+)$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# DEADLINES
# ---------------------------------------------------------------------------

DEADLINE_PATTERN = re.compile(
    r"\b("
    r"by\s+(?:"
    r"monday|"
    r"tuesday|"
    r"wednesday|"
    r"thursday|"
    r"friday|"
    r"saturday|"
    r"sunday|"
    r"tomorrow|"
    r"today|"
    r"next\s+week|"
    r"end\s+of\s+day|"
    r"eod|"
    r"january\s+\d{1,2}|"
    r"february\s+\d{1,2}|"
    r"march\s+\d{1,2}|"
    r"april\s+\d{1,2}|"
    r"may\s+\d{1,2}|"
    r"june\s+\d{1,2}|"
    r"july\s+\d{1,2}|"
    r"august\s+\d{1,2}|"
    r"september\s+\d{1,2}|"
    r"october\s+\d{1,2}|"
    r"november\s+\d{1,2}|"
    r"december\s+\d{1,2}"
    r")|"
    r"before\s+(?:"
    r"monday|"
    r"tuesday|"
    r"wednesday|"
    r"thursday|"
    r"friday|"
    r"saturday|"
    r"sunday|"
    r"tomorrow|"
    r"next\s+week|"
    r"end\s+of\s+day|"
    r"eod"
    r")|"
    r"due\s+(?:"
    r"monday|"
    r"tuesday|"
    r"wednesday|"
    r"thursday|"
    r"friday|"
    r"saturday|"
    r"sunday|"
    r"tomorrow|"
    r"next\s+week|"
    r"end\s+of\s+day|"
    r"eod"
    r")"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# QUESTIONS
# ---------------------------------------------------------------------------

QUESTION_PATTERN = re.compile(
    r"\?\s*$",
    re.IGNORECASE,
)


QUESTION_START_PATTERN = re.compile(
    r"^(?:"
    r"what|"
    r"which|"
    r"how|"
    r"who|"
    r"when|"
    r"where|"
    r"why|"
    r"can|"
    r"could|"
    r"should|"
    r"is|"
    r"are|"
    r"do|"
    r"does"
    r")\b",
    re.IGNORECASE,
)


EXPLICIT_QUESTION_PATTERN = re.compile(
    r"^(?:"
    r"unresolved\s+question|"
    r"open\s+question|"
    r"question"
    r")\s*:",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# RISKS / BLOCKERS
# ---------------------------------------------------------------------------

RISK_PATTERN = re.compile(
    r"\b("
    r"risk|"
    r"delayed|"
    r"delay|"
    r"blocker|"
    r"blocked|"
    r"cannot\s+proceed|"
    r"cannot\s+continue|"
    r"credentials\s+missing|"
    r"pending\s+dependency|"
    r"problem|"
    r"critical\s+issue"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# EXPLICIT ASSIGNMENT
#
# Examples:
#
#   [Thanuja Yennu] Access Register: Access the proposal register.
#   [Bob] Complete API documentation.
# ---------------------------------------------------------------------------

EXPLICIT_ASSIGNEE_PATTERN = re.compile(
    r"^\s*[*\-•]?\s*\[([^\]]+)\]\s*(.+?)\s*$"
)


# ---------------------------------------------------------------------------
# TASK DEPENDENCIES
#
# IMPORTANT:
# Dependencies are extracted ONLY when dependency language is explicitly
# present in the transcript.
#
# task_a = prerequisite
# task_b = dependent task
# ---------------------------------------------------------------------------

# Example:
#
#   Task B setting up Terraform depends on Task A getting AWS credentials.
#
TASK_DEPENDENCY_PATTERN = re.compile(
    r"\b"
    r"(?P<task_b>"
    r"(?:Task|Step|Item|Activity)\s+[A-Za-z0-9_-]+"
    r"(?:\s+[A-Za-z0-9_'-]+)*"
    r")"
    r"\s+depends\s+(?:on|upon)\s+"
    r"(?P<task_a>"
    r"(?:Task|Step|Item|Activity)\s+[A-Za-z0-9_-]+"
    r"(?:\s+[A-Za-z0-9_'-]+)*"
    r")"
    r"(?=[.!?]|$)",
    re.IGNORECASE,
)


# Example:
#
#   Task A getting AWS credentials must be completed before
#   Task B setting up Terraform.
#
TASK_BEFORE_DEPENDENCY_PATTERN = re.compile(
    r"\b"
    r"(?P<task_a>"
    r"(?:Task|Step|Item|Activity)\s+[A-Za-z0-9_-]+"
    r"(?:\s+[A-Za-z0-9_'-]+)*"
    r")"
    r"\s+must\s+be\s+"
    r"(?:completed|finished|done)"
    r"\s+before\s+"
    r"(?P<task_b>"
    r"(?:Task|Step|Item|Activity)\s+[A-Za-z0-9_-]+"
    r"(?:\s+[A-Za-z0-9_'-]+)*"
    r")"
    r"(?=[.!?]|$)",
    re.IGNORECASE,
)


# Generic explicit dependency wording.
#
# Example:
#
#   API deployment requires database migration.
#
GENERIC_DEPENDENCY_PATTERN = re.compile(
    r"(?:^|[.!?]\s*)"
    r"(?P<task_b>[^.!?]+?)"
    r"\s+(?:"
    r"depends\s+(?:on|upon)|"
    r"is\s+dependent\s+on|"
    r"requires"
    r")\s+"
    r"(?P<task_a>[^.!?]+?)"
    r"(?=[.!?]|$)",
    re.IGNORECASE,
)


# ============================================================================
# HELPERS
# ============================================================================

def clean_text(text: str) -> str:
    """
    Remove common transcript artifacts without changing meaning.
    """

    if not text:
        return ""

    text = text.replace("\ufeff", "")

    return text.strip()


def is_metadata_or_ui_text(text: str) -> bool:
    """
    Ignore obvious meeting-note UI/footer text.
    """

    lower = text.lower().strip()

    ignored_phrases = [
        "please rate the new quick notes tab",
        "want to see more? view the full notes",
        "you can always access your full notes",
        "you should review gemini's notes",
        "get tips and learn how gemini takes notes",
    ]

    return any(
        phrase in lower
        for phrase in ignored_phrases
    )


def extract_explicit_assignment(
    text: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract an explicitly assigned action.

    Example:

        [Thanuja Yennu] Access Register:
        Access the proposal register.

    Returns:

        (responsible_person, task_description)
    """

    match = EXPLICIT_ASSIGNEE_PATTERN.match(text)

    if not match:
        return None, None

    responsible = match.group(1).strip()
    task_text = match.group(2).strip()

    if responsible.lower() in {
        "tip",
        "speaker",
        "system",
        "note",
        "unknown",
    }:
        return None, None

    if ":" in task_text:

        _, actual_task = task_text.split(
            ":",
            1,
        )

        if actual_task.strip():
            task_text = actual_task.strip()

    if not task_text:
        return None, None

    return responsible, task_text


def extract_deadline(
    text: str,
) -> Optional[str]:
    """
    Extract only deadlines explicitly present in the transcript.
    """

    match = DEADLINE_PATTERN.search(text)

    if match:
        return match.group(0).strip()

    return None


def format_timestamp(
    seconds: Optional[float],
) -> Optional[str]:
    """
    Convert real transcript seconds into MM:SS.

    Never manufacture a timestamp.
    """

    if seconds is None:
        return None

    try:
        seconds_float = float(seconds)
    except (TypeError, ValueError):
        return None

    if seconds_float < 0:
        return None

    mins = int(seconds_float // 60)
    secs = int(seconds_float % 60)

    return f"{mins:02d}:{secs:02d}"


def deduplicate(
    items: List[Dict[str, Any]],
    key: str,
) -> List[Dict[str, Any]]:
    """
    Remove duplicate extracted items.
    """

    seen = set()
    result = []

    for item in items:

        value = item.get(key)

        if value is None:
            continue

        value = str(value).strip().lower()

        if not value:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(item)

    return result


def extract_task_dependency(
    text: str,
) -> Optional[Dict[str, str]]:
    """
    Extract only explicitly stated task dependencies.

    Examples:

        Task B setting up Terraform depends on Task A getting AWS credentials.

        Task A getting AWS credentials must be completed before
        Task B setting up Terraform.

        API deployment requires database migration.

    task_a = prerequisite
    task_b = dependent task

    No dependency is inferred from task ordering.
    """

    cleaned = clean_text(text)

    if not cleaned:
        return None

    # -----------------------------------------------------------------------
    # 1. "Task B depends on Task A"
    # -----------------------------------------------------------------------

    match = TASK_DEPENDENCY_PATTERN.search(cleaned)

    if match:

        task_b = match.group("task_b").strip()
        task_a = match.group("task_a").strip()

        task_b = task_b.rstrip(" .!?")
        task_a = task_a.rstrip(" .!?")

        if task_a and task_b:

            return {
                "task_a": task_a,
                "task_b": task_b,
                "dependency_description": cleaned,
            }

    # -----------------------------------------------------------------------
    # 2. "Task A must be completed before Task B"
    # -----------------------------------------------------------------------

    match = TASK_BEFORE_DEPENDENCY_PATTERN.search(
        cleaned
    )

    if match:

        task_a = match.group("task_a").strip()
        task_b = match.group("task_b").strip()

        task_a = task_a.rstrip(" .!?")
        task_b = task_b.rstrip(" .!?")

        if task_a and task_b:

            return {
                "task_a": task_a,
                "task_b": task_b,
                "dependency_description": cleaned,
            }

    # -----------------------------------------------------------------------
    # 3. Generic explicit dependency
    # -----------------------------------------------------------------------

    match = GENERIC_DEPENDENCY_PATTERN.search(
        cleaned
    )

    if match:

        task_b = match.group("task_b").strip()
        task_a = match.group("task_a").strip()

        task_b = task_b.rstrip(" .!?")
        task_a = task_a.rstrip(" .!?")

        if not task_a or not task_b:
            return None

        # Avoid accepting huge accidental captures.
        if len(task_a) > 500 or len(task_b) > 500:
            return None

        return {
            "task_a": task_a,
            "task_b": task_b,
            "dependency_description": cleaned,
        }

    return None


def extract_named_action(
    text: str,
    known_speakers: List[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract a named person's explicit commitment.

    Example:

        Bob will complete the Terraform configuration by Friday.

    Only names already present in transcript speaker metadata
    are accepted.
    """

    if not text or not known_speakers:
        return None, None

    for speaker_name in known_speakers:

        if not speaker_name:
            continue

        pattern = re.compile(
            rf"^\s*{re.escape(speaker_name)}\s+"
            r"(?:will|shall|is\s+going\s+to)\s+"
            r"(.+?)\s*$",
            re.IGNORECASE,
        )

        match = pattern.match(text)

        if match:

            task = match.group(1).strip()

            if task:
                return speaker_name, task

    return None, None


# ============================================================================
# MAIN GROUNDED INTELLIGENCE EXTRACTION
# ============================================================================

def classify_and_extract_intelligence(
    segments: List[models.TranscriptSegment],
) -> Dict[str, Any]:

    decisions = []
    action_items = []
    unresolved_questions = []
    topics = []
    important_moments = []
    risks_blockers = []
    dependencies = []
    timeline_events = []
    follow_up_suggestions = []

    meaningful_segments = []

    # -----------------------------------------------------------------------
    # Build grounded speaker list.
    # -----------------------------------------------------------------------

    known_speakers = []

    for seg in segments:

        speaker_name = (
            seg.speaker_name
            or seg.speaker_label
            or None
        )

        if speaker_name:

            speaker_name = str(
                speaker_name
            ).strip()

            if (
                speaker_name
                and speaker_name not in known_speakers
            ):
                known_speakers.append(
                    speaker_name
                )

    # -----------------------------------------------------------------------
    # PROCESS TRANSCRIPT SEGMENTS
    # -----------------------------------------------------------------------

    for seg in segments:

        text = clean_text(seg.text)

        if not text:
            continue

        if is_metadata_or_ui_text(text):
            continue

        meaningful_segments.append(seg)

        speaker = (
            seg.speaker_name
            or seg.speaker_label
            or None
        )

        lower = text.lower()

        # -------------------------------------------------------------------
        # TIMELINE
        #
        # Only real transcript timestamps are accepted.
        # -------------------------------------------------------------------

        if seg.start_time is not None:

            time_str = format_timestamp(
                seg.start_time
            )

            if time_str is not None:

                timeline_events.append({
                    "event_time_str": time_str,
                    "timestamp_seconds": float(
                        seg.start_time
                    ),
                    "event_title": (
                        f"Meeting event: "
                        f"{speaker or 'Speaker'}"
                    ),
                    "event_description": text,
                    "segment_id": seg.id,
                    "context_quote": text,
                })

        # -------------------------------------------------------------------
        # TASK DEPENDENCY
        # -------------------------------------------------------------------

        dependency = extract_task_dependency(
            text
        )

        if dependency:

            dependencies.append({
                "task_a": dependency["task_a"],
                "task_b": dependency["task_b"],
                "dependency_description": (
                    dependency[
                        "dependency_description"
                    ]
                ),
                "context_quote": text,
            })

            important_moments.append({
                "moment_type": "Dependency",
                "description": (
                    dependency[
                        "dependency_description"
                    ]
                ),
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

        # -------------------------------------------------------------------
        # EXPLICIT [PERSON] ACTION
        # -------------------------------------------------------------------

        explicit_person, explicit_task = (
            extract_explicit_assignment(text)
        )

        if explicit_person and explicit_task:

            deadline = extract_deadline(
                explicit_task
            )

            action_items.append({
                "task_description": explicit_task,
                "responsible_person": explicit_person,
                "deadline": deadline,
                "status": "pending",
                "priority": (
                    "high"
                    if deadline
                    else "medium"
                ),
                "context_quote": text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

            important_moments.append({
                "moment_type": "Action Item",
                "description": (
                    f"Action assigned to "
                    f"{explicit_person}: "
                    f"{explicit_task}"
                ),
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

        else:

            # ---------------------------------------------------------------
            # DECISION EXTRACTION
            # ---------------------------------------------------------------

            explicit_decision_match = (
                EXPLICIT_DECISION_PREFIX_PATTERN.match(
                    text
                )
            )

            pattern_decision_match = (
                DECISION_PATTERN.search(text)
            )

            is_confirmed_decision = (
                explicit_decision_match is not None
                or (
                    pattern_decision_match is not None
                    and not SUGGESTION_PATTERN.search(
                        text
                    )
                )
            )

            if is_confirmed_decision:

                if explicit_decision_match:

                    decision_text = (
                        explicit_decision_match
                        .group(1)
                        .strip()
                    )

                else:

                    decision_text = text

                decisions.append({
                    "decision_text": decision_text,
                    "context_quote": text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "confidence": "high",
                })

                important_moments.append({
                    "moment_type": "Decision",
                    "description": (
                        f"Decision agreed: "
                        f"{decision_text}"
                    ),
                    "context_quote": text,
                    "segment_id": seg.id,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "confidence": "high",
                })

            # ---------------------------------------------------------------
            # ACTION ITEM EXTRACTION
            #
            # Do not treat a confirmed decision itself as an action item.
            # ---------------------------------------------------------------

            action_text = ""

            if not is_confirmed_decision:

                action_text = text

            if action_text:

                explicit_action_match = (
                    EXPLICIT_ACTION_PREFIX_PATTERN.match(
                        action_text
                    )
                )

                if explicit_action_match:

                    action_text = (
                        explicit_action_match
                        .group(1)
                        .strip()
                    )

                # -----------------------------------------------------------
                # Named action:
                #
                # Bob will complete the Terraform configuration.
                # -----------------------------------------------------------

                named_person, named_task = (
                    extract_named_action(
                        action_text,
                        known_speakers,
                    )
                )

                # -----------------------------------------------------------
                # Standard action patterns
                # -----------------------------------------------------------

                direct_action_match = (
                    DIRECT_ACTION_PATTERN.search(
                        action_text
                    )
                )

                unassigned_action_match = (
                    UNASSIGNED_ACTION_PATTERN.search(
                        action_text
                    )
                )

                if (
                    named_person
                    or direct_action_match
                    or unassigned_action_match
                ):

                    if named_person:

                        responsible = named_person

                    elif unassigned_action_match:

                        responsible = None

                    else:

                        responsible = speaker

                    deadline = extract_deadline(
                        action_text
                    )

                    task_description = (
                        named_task
                        if named_person and named_task
                        else action_text
                    )

                    action_items.append({
                        "task_description": (
                            task_description
                        ),
                        "responsible_person": (
                            responsible
                        ),
                        "deadline": deadline,
                        "status": "pending",
                        "priority": (
                            "high"
                            if deadline
                            else "medium"
                        ),
                        "context_quote": text,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "confidence": (
                            "high"
                            if responsible
                            else "medium"
                        ),
                    })

                    important_moments.append({
                        "moment_type": "Action Item",
                        "description": (
                            f"Action assigned to "
                            f"{responsible or 'Unassigned'}: "
                            f"{task_description}"
                        ),
                        "context_quote": text,
                        "segment_id": seg.id,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "confidence": (
                            "high"
                            if responsible
                            else "medium"
                        ),
                    })

        # -------------------------------------------------------------------
        # UNRESOLVED QUESTIONS
        # -------------------------------------------------------------------

        is_question = (
            bool(
                QUESTION_PATTERN.search(text)
            )
            or bool(
                QUESTION_START_PATTERN.search(text)
            )
            or bool(
                EXPLICIT_QUESTION_PATTERN.search(text)
            )
        )

        if is_question:

            unresolved_questions.append({
                "question": text,
                "context_quote": text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

            important_moments.append({
                "moment_type": "Question",
                "description": (
                    f"Question raised: {text}"
                ),
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

        # -------------------------------------------------------------------
        # RISKS / BLOCKERS
        # -------------------------------------------------------------------

        if RISK_PATTERN.search(text):

            is_blocker = (
                "blocker" in lower
                or "blocked" in lower
                or "cannot proceed" in lower
                or "cannot continue" in lower
            )

            item_type = (
                "blocker"
                if is_blocker
                else "risk"
            )

            risks_blockers.append({
                "title": item_type.capitalize(),
                "description": text,
                "item_type": item_type,
                "status": "open",
                "responsible_person": speaker,
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
            })

            important_moments.append({
                "moment_type": item_type.capitalize(),
                "description": text,
                "context_quote": text,
                "segment_id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "confidence": "high",
            })

        # -------------------------------------------------------------------
        # TOPIC EXTRACTION
        # -------------------------------------------------------------------

        topic_rules = [
            (
                [
                    "proposal register",
                    "proposal",
                ],
                "Proposal Register",
            ),
            (
                [
                    "meeting date",
                    "meeting dates",
                    "date discussed",
                ],
                "Meeting Dates",
            ),
            (
                [
                    "university",
                ],
                "University / Organization Discussion",
            ),
            (
                [
                    "database",
                    "postgresql",
                    "mysql",
                    "mongodb",
                ],
                "Database",
            ),
            (
                [
                    "api",
                    "endpoint",
                ],
                "API / Backend",
            ),
            (
                [
                    "testing",
                    "test",
                ],
                "Testing",
            ),
            (
                [
                    "deployment",
                    "deploy",
                    "production",
                ],
                "Deployment",
            ),
            (
                [
                    "documentation",
                    "document",
                ],
                "Documentation",
            ),
            (
                [
                    "security",
                    "compliance",
                ],
                "Security & Compliance",
            ),
        ]

        for keywords, topic_title in topic_rules:

            if any(
                keyword in lower
                for keyword in keywords
            ):

                topics.append({
                    "title": topic_title,
                    "description": (
                        f"Discussion related to "
                        f"{topic_title.lower()}."
                    ),
                    "importance": "medium",
                    "context_quote": text,
                    "segment_id": seg.id,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                })

                break

    # =========================================================================
    # DEDUPLICATION
    # =========================================================================

    decisions = deduplicate(
        decisions,
        "decision_text",
    )

    action_items = deduplicate(
        action_items,
        "task_description",
    )

    unresolved_questions = deduplicate(
        unresolved_questions,
        "question",
    )

    risks_blockers = deduplicate(
        risks_blockers,
        "description",
    )

    important_moments = deduplicate(
        important_moments,
        "description",
    )

    topics = deduplicate(
        topics,
        "title",
    )

    # -------------------------------------------------------------------------
    # Dependency deduplication.
    #
    # task_a + task_b uniquely identify a dependency.
    # -------------------------------------------------------------------------

    unique_dependencies = {}

    for dependency in dependencies:

        task_a = (
            dependency["task_a"]
            .strip()
            .lower()
        )

        task_b = (
            dependency["task_b"]
            .strip()
            .lower()
        )

        key = (
            task_a,
            task_b,
        )

        if key not in unique_dependencies:

            unique_dependencies[key] = dependency

    dependencies = list(
        unique_dependencies.values()
    )

    # =========================================================================
    # REMOVE QUESTIONS THAT ARE EXPLICITLY RESOLVED
    # =========================================================================

    final_questions = []

    for question in unresolved_questions:

        q_text = question["question"].lower()

        resolved = False

        for decision in decisions:

            decision_text = (
                decision["decision_text"]
                .lower()
            )

            if decision_text in q_text:

                resolved = True
                break

        if not resolved:

            final_questions.append(
                question
            )

    unresolved_questions = final_questions

    # =========================================================================
    # TOPIC FALLBACK
    # =========================================================================

    if not topics and meaningful_segments:

        first_segment = meaningful_segments[0]

        topics = [{
            "title": "General Discussion",
            "description": (
                f"General discussion covering "
                f"{len(meaningful_segments)} meaningful "
                f"transcript segments."
            ),
            "importance": "medium",
            "context_quote": clean_text(
                first_segment.text
            ),
            "segment_id": first_segment.id,
            "start_time": first_segment.start_time,
            "end_time": first_segment.end_time,
        }]

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================

    executive_parts = []

    executive_parts.append(
        f"The meeting contained "
        f"{len(meaningful_segments)} meaningful "
        f"transcript segments."
    )

    if topics:

        executive_parts.append(
            "Key topics included "
            + ", ".join(
                topic["title"]
                for topic in topics[:5]
            )
            + "."
        )

    if decisions:

        executive_parts.append(
            f"{len(decisions)} explicit decision(s) "
            f"were identified."
        )

    else:

        executive_parts.append(
            "No explicit confirmed decisions "
            "were identified."
        )

    if action_items:

        executive_parts.append(
            f"{len(action_items)} action item(s) "
            f"were identified."
        )

    else:

        executive_parts.append(
            "No explicit action items were identified."
        )

    if unresolved_questions:

        executive_parts.append(
            f"{len(unresolved_questions)} unresolved "
            f"question(s) remain."
        )

    if dependencies:

        executive_parts.append(
            f"{len(dependencies)} explicit task "
            f"dependency/dependencies were identified."
        )

    executive_summary = " ".join(
        executive_parts
    )

    # =========================================================================
    # DETAILED SUMMARY
    # =========================================================================

    detailed_sections = [
        {
            "section_title": "Meeting Overview",
            "points": [
                (
                    f"{len(meaningful_segments)} meaningful "
                    f"transcript segments were analyzed."
                )
            ],
        }
    ]

    for topic in topics:

        detailed_sections.append({
            "section_title": (
                f"Topic: {topic['title']}"
            ),
            "points": [
                topic["description"],
                (
                    f"Evidence: "
                    f"\"{topic['context_quote']}\""
                ),
            ],
        })

    if action_items:

        detailed_sections.append({
            "section_title": "Action Items",
            "points": [
                (
                    f"{item['responsible_person'] or 'Responsible person not identified'}: "
                    f"{item['task_description']}"
                    + (
                        f" (Deadline: {item['deadline']})"
                        if item["deadline"]
                        else " (Deadline: Not specified)"
                    )
                )
                for item in action_items
            ],
        })

    if decisions:

        detailed_sections.append({
            "section_title": "Decisions",
            "points": [
                decision["decision_text"]
                for decision in decisions
            ],
        })

    if dependencies:

        detailed_sections.append({
            "section_title": "Task Dependencies",
            "points": [
                (
                    f"{dependency['task_b']} depends on "
                    f"{dependency['task_a']}."
                )
                for dependency in dependencies
            ],
        })

    if unresolved_questions:

        detailed_sections.append({
            "section_title": "Unresolved Questions",
            "points": [
                question["question"]
                for question in unresolved_questions
            ],
        })

    detailed_sections.append({
        "section_title": "Final Outcomes & Next Steps",
        "points": [
            f"Decisions: {len(decisions)} confirmed",
            f"Action Items: {len(action_items)} identified",
            (
                f"Unresolved Questions: "
                f"{len(unresolved_questions)} open"
            ),
            (
                f"Task Dependencies: "
                f"{len(dependencies)} identified"
            ),
        ],
    })

    detailed_summary_json = json.dumps(
        detailed_sections,
        ensure_ascii=False,
    )

    # =========================================================================
    # FOLLOW-UP PLAN
    # =========================================================================

    follow_up_lines = []

    if action_items:

        follow_up_lines.extend(
            [
                (
                    f"- "
                    f"{item['responsible_person'] or 'Unassigned'}: "
                    f"{item['task_description']}"
                    + (
                        f" (Due: {item['deadline']})"
                        if item["deadline"]
                        else " (Due: Not specified)"
                    )
                )
                for item in action_items
            ]
        )

    if dependencies:

        follow_up_lines.extend(
            [
                (
                    f"- Dependency: "
                    f"{dependency['task_b']} depends on "
                    f"{dependency['task_a']}."
                )
                for dependency in dependencies
            ]
        )

    if follow_up_lines:

        follow_up_plan = "\n".join(
            follow_up_lines
        )

    else:

        follow_up_plan = (
            "No explicit action items requiring follow-up."
        )

    # =========================================================================
    # AI SUGGESTIONS
    # =========================================================================

    if action_items:

        follow_up_suggestions.append({
            "suggestion_text": (
                "Review the identified action items with "
                "the responsible participants during "
                "the next follow-up."
            ),
            "category": "action_item_review",
        })

    if unresolved_questions:

        follow_up_suggestions.append({
            "suggestion_text": (
                "Review unresolved questions before "
                "the next meeting."
            ),
            "category": "question_resolution",
        })

    if risks_blockers:

        follow_up_suggestions.append({
            "suggestion_text": (
                "Review the identified risks or blockers "
                "before the next project checkpoint."
            ),
            "category": "risk_management",
        })

    if dependencies:

        follow_up_suggestions.append({
            "suggestion_text": (
                "Review the identified task dependencies "
                "before starting dependent tasks."
            ),
            "category": "dependency_management",
        })

    # =========================================================================
    # TONE / OUTCOME
    # =========================================================================

    if risks_blockers:

        conversational_tone = "tense"

    elif decisions:

        conversational_tone = "positive"

    else:

        conversational_tone = "neutral"

    tone_explanation = (
        f"Tone classified as {conversational_tone} based on "
        f"{len(decisions)} decision(s), "
        f"{len(action_items)} action item(s), and "
        f"{len(risks_blockers)} risk/blocker(s)."
    )

    if (
        decisions
        and action_items
        and not unresolved_questions
    ):

        meeting_outcome = "completed"

    elif decisions or action_items:

        meeting_outcome = "partially_completed"

    elif unresolved_questions:

        meeting_outcome = "unresolved"

    else:

        meeting_outcome = "informational"

    # =========================================================================
    # FINAL RESULT
    # =========================================================================

    return {
        "overview": (
            f"Meeting discussion covering "
            f"{len(meaningful_segments)} meaningful "
            f"transcript segments."
        ),
        "follow_up_plan": follow_up_plan,
        "executive_summary": executive_summary,
        "detailed_summary_json": detailed_summary_json,
        "conversational_tone": conversational_tone,
        "tone_explanation": tone_explanation,
        "meeting_outcome": meeting_outcome,
        "decisions": decisions,
        "action_items": action_items,
        "unresolved_questions": unresolved_questions,
        "topics": topics,
        "important_moments": important_moments,
        "risks_blockers": risks_blockers,
        "dependencies": dependencies,
        "timeline_events": timeline_events,
        "follow_up_suggestions": follow_up_suggestions,
    }


# ============================================================================
# DATABASE PROCESSING
# ============================================================================

def process_meeting_analysis(
    meeting_id: str,
    db: Session,
) -> models.Meeting:

    meeting = (
        db.query(models.Meeting)
        .filter(
            models.Meeting.id == meeting_id
        )
        .first()
    )

    if not meeting:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Meeting with ID '{meeting_id}' "
                f"not found."
            ),
        )

    segments = (
        db.query(models.TranscriptSegment)
        .filter(
            models.TranscriptSegment.meeting_id
            == meeting_id
        )
        .order_by(
            models.TranscriptSegment.id
        )
        .all()
    )

    if not segments:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No transcript segments found for "
                f"meeting '{meeting_id}'. "
                f"Please process or transcribe "
                f"meeting first."
            ),
        )

    result = classify_and_extract_intelligence(
        segments
    )

    # -----------------------------------------------------------------------
    # CLEAR PREVIOUS ANALYSIS
    # -----------------------------------------------------------------------

    db.query(models.Decision).filter(
        models.Decision.meeting_id
        == meeting_id
    ).delete()

    db.query(models.ActionItem).filter(
        models.ActionItem.meeting_id
        == meeting_id
    ).delete()

    db.query(models.UnresolvedQuestion).filter(
        models.UnresolvedQuestion.meeting_id
        == meeting_id
    ).delete()

    db.query(models.MeetingSummary).filter(
        models.MeetingSummary.meeting_id
        == meeting_id
    ).delete()

    db.query(models.MeetingTopic).filter(
        models.MeetingTopic.meeting_id
        == meeting_id
    ).delete()

    db.query(models.ImportantMoment).filter(
        models.ImportantMoment.meeting_id
        == meeting_id
    ).delete()

    db.query(models.MeetingRiskBlocker).filter(
        models.MeetingRiskBlocker.meeting_id
        == meeting_id
    ).delete()

    db.query(models.TaskDependency).filter(
        models.TaskDependency.meeting_id
        == meeting_id
    ).delete()

    db.query(models.TimelineEvent).filter(
        models.TimelineEvent.meeting_id
        == meeting_id
    ).delete()

    db.query(models.FollowUpSuggestion).filter(
        models.FollowUpSuggestion.meeting_id
        == meeting_id
    ).delete()

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------

    db.add(
        models.MeetingSummary(
            meeting_id=meeting_id,
            overview=result["overview"],
            follow_up_plan=result["follow_up_plan"],
            executive_summary=result[
                "executive_summary"
            ],
            detailed_summary_json=result[
                "detailed_summary_json"
            ],
            conversational_tone=result[
                "conversational_tone"
            ],
            tone_explanation=result[
                "tone_explanation"
            ],
            meeting_outcome=result[
                "meeting_outcome"
            ],
        )
    )

    # -----------------------------------------------------------------------
    # DECISIONS
    # -----------------------------------------------------------------------

    db.add_all([
        models.Decision(
            meeting_id=meeting_id,
            decision_text=d["decision_text"],
            context_quote=d["context_quote"],
            start_time=d["start_time"],
            end_time=d["end_time"],
            confidence=d["confidence"],
        )
        for d in result["decisions"]
    ])

    # -----------------------------------------------------------------------
    # ACTION ITEMS
    # -----------------------------------------------------------------------

    db.add_all([
        models.ActionItem(
            meeting_id=meeting_id,
            task_description=a["task_description"],
            responsible_person=a[
                "responsible_person"
            ],
            deadline=a["deadline"],
            status=a["status"],
            priority=a["priority"],
            context_quote=a["context_quote"],
            start_time=a["start_time"],
            end_time=a["end_time"],
            confidence=a["confidence"],
        )
        for a in result["action_items"]
    ])

    # -----------------------------------------------------------------------
    # UNRESOLVED QUESTIONS
    # -----------------------------------------------------------------------

    db.add_all([
        models.UnresolvedQuestion(
            meeting_id=meeting_id,
            question=q["question"],
            context_quote=q["context_quote"],
            start_time=q["start_time"],
            end_time=q["end_time"],
            confidence=q["confidence"],
        )
        for q in result[
            "unresolved_questions"
        ]
    ])

    # -----------------------------------------------------------------------
    # TOPICS
    # -----------------------------------------------------------------------

    db.add_all([
        models.MeetingTopic(
            meeting_id=meeting_id,
            title=t["title"],
            description=t["description"],
            importance=t["importance"],
            context_quote=t["context_quote"],
            segment_id=t.get("segment_id"),
            start_time=t.get("start_time"),
            end_time=t.get("end_time"),
        )
        for t in result["topics"]
    ])

    # -----------------------------------------------------------------------
    # IMPORTANT MOMENTS
    # -----------------------------------------------------------------------

    db.add_all([
        models.ImportantMoment(
            meeting_id=meeting_id,
            moment_type=m["moment_type"],
            description=m["description"],
            context_quote=m["context_quote"],
            segment_id=m.get("segment_id"),
            start_time=m.get("start_time"),
            end_time=m.get("end_time"),
            confidence=m.get(
                "confidence",
                "high",
            ),
        )
        for m in result[
            "important_moments"
        ]
    ])

    # -----------------------------------------------------------------------
    # RISKS / BLOCKERS
    # -----------------------------------------------------------------------

    db.add_all([
        models.MeetingRiskBlocker(
            meeting_id=meeting_id,
            title=r["title"],
            description=r["description"],
            item_type=r["item_type"],
            status=r.get(
                "status",
                "open",
            ),
            responsible_person=r.get(
                "responsible_person"
            ),
            context_quote=r["context_quote"],
            segment_id=r.get("segment_id"),
            start_time=r.get("start_time"),
            end_time=r.get("end_time"),
        )
        for r in result[
            "risks_blockers"
        ]
    ])

    # -----------------------------------------------------------------------
    # TASK DEPENDENCIES
    #
    # task_a = prerequisite
    # task_b = dependent task
    # -----------------------------------------------------------------------

    db.add_all([
        models.TaskDependency(
            meeting_id=meeting_id,
            task_a=dependency["task_a"],
            task_b=dependency["task_b"],
            dependency_description=dependency[
                "dependency_description"
            ],
            context_quote=dependency[
                "context_quote"
            ],
        )
        for dependency in result[
            "dependencies"
        ]
    ])

    # -----------------------------------------------------------------------
    # TIMELINE
    # -----------------------------------------------------------------------

    db.add_all([
        models.TimelineEvent(
            meeting_id=meeting_id,
            event_time_str=event[
                "event_time_str"
            ],
            timestamp_seconds=event[
                "timestamp_seconds"
            ],
            event_title=event[
                "event_title"
            ],
            event_description=event[
                "event_description"
            ],
            segment_id=event.get(
                "segment_id"
            ),
            context_quote=event[
                "context_quote"
            ],
        )
        for event in result[
            "timeline_events"
        ]
    ])

    # -----------------------------------------------------------------------
    # FOLLOW-UP SUGGESTIONS
    # -----------------------------------------------------------------------

    db.add_all([
        models.FollowUpSuggestion(
            meeting_id=meeting_id,
            suggestion_text=s[
                "suggestion_text"
            ],
            category=s.get(
                "category",
                "general",
            ),
        )
        for s in result[
            "follow_up_suggestions"
        ]
    ])

    # -----------------------------------------------------------------------
    # FINAL MEETING STATUS
    # -----------------------------------------------------------------------

    meeting.status = "ANALYZED"

    db.commit()
    db.refresh(meeting)

    return meeting


# ============================================================================
# GET MEETING ANALYSIS
# ============================================================================

def get_meeting_analysis(
    meeting_id: str,
    db: Session,
) -> Dict[str, Any]:

    meeting = (
        db.query(models.Meeting)
        .filter(
            models.Meeting.id == meeting_id
        )
        .first()
    )

    if not meeting:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Meeting with ID '{meeting_id}' "
                f"not found."
            ),
        )

    summary = (
        db.query(models.MeetingSummary)
        .filter(
            models.MeetingSummary.meeting_id
            == meeting_id
        )
        .first()
    )

    decisions = (
        db.query(models.Decision)
        .filter(
            models.Decision.meeting_id
            == meeting_id
        )
        .all()
    )

    action_items = (
        db.query(models.ActionItem)
        .filter(
            models.ActionItem.meeting_id
            == meeting_id
        )
        .all()
    )

    unresolved_questions = (
        db.query(models.UnresolvedQuestion)
        .filter(
            models.UnresolvedQuestion.meeting_id
            == meeting_id
        )
        .all()
    )

    topics = (
        db.query(models.MeetingTopic)
        .filter(
            models.MeetingTopic.meeting_id
            == meeting_id
        )
        .all()
    )

    important_moments = (
        db.query(models.ImportantMoment)
        .filter(
            models.ImportantMoment.meeting_id
            == meeting_id
        )
        .all()
    )

    risks_blockers = (
        db.query(models.MeetingRiskBlocker)
        .filter(
            models.MeetingRiskBlocker.meeting_id
            == meeting_id
        )
        .all()
    )

    dependencies = (
        db.query(models.TaskDependency)
        .filter(
            models.TaskDependency.meeting_id
            == meeting_id
        )
        .all()
    )

    timeline_events = (
        db.query(models.TimelineEvent)
        .filter(
            models.TimelineEvent.meeting_id
            == meeting_id
        )
        .order_by(
            models.TimelineEvent.timestamp_seconds
        )
        .all()
    )

    follow_up_suggestions = (
        db.query(
            models.FollowUpSuggestion
        )
        .filter(
            models.FollowUpSuggestion.meeting_id
            == meeting_id
        )
        .all()
    )

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
        "follow_up_suggestions": follow_up_suggestions,
    }