import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

def normalize_deadline(
    deadline_str: Optional[str],
    base_date: Optional[datetime] = None,
    user_tz: str = "Asia/Kolkata"
) -> Tuple[Optional[datetime], str]:
    """
    Normalizes natural language deadlines ('by Friday', 'tomorrow', 'next Monday', ISO dates)
    into timezone-aware datetime objects.
    Returns (normalized_datetime, timezone_string).
    If unresolvable or ambiguous ('soon', 'later', None), returns (None, user_tz) to prevent guessing.
    """
    if not deadline_str or not isinstance(deadline_str, str):
        return None, user_tz

    cleaned = deadline_str.strip().lower()
    if not cleaned or cleaned in ("not specified", "unmentioned", "soon", "later", "vague"):
        return None, user_tz

    if base_date is None:
        base_date = datetime.now(timezone.utc)
    elif base_date.tzinfo is None:
        base_date = base_date.replace(tzinfo=timezone.utc)

    # 1. ISO Date parsing (e.g. 2026-09-25 or 2026-10-15T14:30:00Z)
    iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', cleaned)
    if iso_match:
        try:
            year, month, day = map(int, iso_match.groups())
            dt = datetime(year, month, day, 17, 0, 0, tzinfo=timezone.utc)
            return dt, user_tz
        except ValueError:
            pass

    # 2. Today / Tomorrow
    if "today" in cleaned:
        dt = base_date.replace(hour=17, minute=0, second=0, microsecond=0)
        return dt, user_tz
    if "tomorrow" in cleaned:
        dt = (base_date + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        return dt, user_tz

    # 3. Weekday parsing ("by Friday", "next Monday", "on Tuesday")
    days_of_week = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    for day_name, day_num in days_of_week.items():
        if day_name in cleaned:
            current_day = base_date.weekday()
            days_ahead = day_num - current_day
            if days_ahead <= 0:  # Target day already passed this week, move to next week
                days_ahead += 7
            if "next" in cleaned and days_ahead < 7:
                days_ahead += 7

            dt = (base_date + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
            return dt, user_tz

    # 4. End of week / End of month
    if "end of week" in cleaned or "end of this week" in cleaned:
        days_ahead = 4 - base_date.weekday()  # Friday
        if days_ahead <= 0:
            days_ahead += 7
        dt = (base_date + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
        return dt, user_tz

    if "end of month" in cleaned or "end of this month" in cleaned:
        # First day of next month minus 1 day
        next_month = base_date.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        dt = last_day.replace(hour=17, minute=0, second=0, microsecond=0)
        return dt, user_tz

    # Unresolvable deadline -> Return None without guessing
    return None, user_tz
