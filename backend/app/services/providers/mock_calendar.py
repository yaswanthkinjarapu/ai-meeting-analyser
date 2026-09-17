import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.providers.base_calendar import BaseCalendarProvider

class MockCalendarProvider(BaseCalendarProvider):
    def __init__(self):
        self.events: Dict[str, Dict[str, Any]] = {}

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        ext_id = f"mock_cal_event_{uuid.uuid4().hex[:8]}"
        event_record = {
            "external_event_id": ext_id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": description,
            "timezone": timezone,
            "status": "confirmed"
        }
        self.events[ext_id] = event_record
        return event_record

    def update_event(
        self,
        external_event_id: str,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        if external_event_id not in self.events:
            ext_record = {"external_event_id": external_event_id, "status": "updated"}
        else:
            ext_record = self.events[external_event_id]

        if title:
            ext_record["title"] = title
        if start_time:
            ext_record["start_time"] = start_time.isoformat()
        if end_time:
            ext_record["end_time"] = end_time.isoformat()
        if description:
            ext_record["description"] = description
        return ext_record

    def delete_event(self, external_event_id: str) -> bool:
        if external_event_id in self.events:
            del self.events[external_event_id]
        return True

    def test_connection(self) -> bool:
        return True
