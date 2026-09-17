from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseEmailProvider(ABC):
    @abstractmethod
    def create_draft(
        self,
        recipient: Optional[str],
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Creates an email draft. Returns dict with external_draft_id and status."""
        pass

    @abstractmethod
    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Sends an email after explicit user confirmation."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Tests email integration connection status."""
        pass
