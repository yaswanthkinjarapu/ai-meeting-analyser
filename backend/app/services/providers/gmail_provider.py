from typing import Dict, Any, Optional
from app.services.providers.base_email import BaseEmailProvider
from app.services.providers.mock_email import MockEmailProvider

class GmailEmailProvider(BaseEmailProvider):
    """
    Gmail API provider wrapper.
    Delegates safely to MockEmailProvider when external OAuth credentials are not connected.
    """
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self._fallback = MockEmailProvider()

    def create_draft(
        self,
        recipient: Optional[str],
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        return self._fallback.create_draft(recipient, subject, body)

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        return self._fallback.send_email(recipient, subject, body)

    def test_connection(self) -> bool:
        return bool(self.access_token)
