import uuid
from typing import Dict, Any, Optional
from app.services.providers.base_email import BaseEmailProvider

class MockEmailProvider(BaseEmailProvider):
    def __init__(self):
        self.drafts: Dict[str, Dict[str, Any]] = {}
        self.sent: Dict[str, Dict[str, Any]] = {}

    def create_draft(
        self,
        recipient: Optional[str],
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        ext_id = f"mock_email_draft_{uuid.uuid4().hex[:8]}"
        draft_record = {
            "external_draft_id": ext_id,
            "recipient": recipient or "Not specified",
            "subject": subject,
            "body": body,
            "status": "DRAFT"
        }
        self.drafts[ext_id] = draft_record
        return draft_record

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        ext_id = f"mock_email_sent_{uuid.uuid4().hex[:8]}"
        sent_record = {
            "external_id": ext_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "SENT"
        }
        self.sent[ext_id] = sent_record
        return sent_record

    def test_connection(self) -> bool:
        return True
