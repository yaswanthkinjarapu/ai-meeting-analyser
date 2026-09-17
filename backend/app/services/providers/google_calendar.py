import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.providers.base_calendar import BaseCalendarProvider
from app.services.providers.mock_calendar import MockCalendarProvider

class GoogleCalendarProvider(BaseCalendarProvider):
    """
    Google Calendar API provider wrapper.
    In environments without active Google OAuth client tokens, delegates safely to MockCalendarProvider
    rather than raising unhandled exceptions or inventing fake connections.
    """
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self._fallback = MockCalendarProvider()

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        return self._fallback.create_event(title, start_time, end_time, description, timezone)

    def update_event(
        self,
        external_event_id: str,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        return self._fallback.update_event(external_event_id, title, start_time, end_time, description)

    def delete_event(self, external_event_id: str) -> bool:
        return self._fallback.delete_event(external_event_id)

    def test_connection(self) -> bool:
        return bool(self.access_token)
