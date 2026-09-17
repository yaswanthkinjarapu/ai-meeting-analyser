from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

class BaseCalendarProvider(ABC):
    @abstractmethod
    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Creates a calendar event. Returns dict with external_event_id and status."""
        pass

    @abstractmethod
    def update_event(
        self,
        external_event_id: str,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates an existing calendar event."""
        pass

    @abstractmethod
    def delete_event(self, external_event_id: str) -> bool:
        """Deletes/cancels a calendar event."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Tests calendar integration connection status."""
        pass
