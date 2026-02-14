"""Background email poller for dev mode — polls AgentMail REST API every 10s."""
import re
import threading
import requests
from urllib.parse import quote


API_BASE = "https://api.agentmail.to/v0"


def _parse_email(from_field: str) -> str:
    """Extract bare email from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', from_field)
    if match:
        return match.group(1)
    return from_field.strip()


class EmailPoller:
    def __init__(self, app=None):
        self.app = app
        self._thread = None
        self._stop_event = threading.Event()

    def init_app(self, app):
        self.app = app

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("Email poller started (polling every 10s)", flush=True)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                with self.app.app_context():
                    self._check_inboxes()
            except Exception as e:
                print(f"Poller error: {e}", flush=True)
            self._stop_event.wait(10)

    def _headers(self):
        from ..config import Config
        return {
            "Authorization": f"Bearer {Config.AGENTMAIL_API_KEY}",
            "Content-Type": "application/json",
        }

    def _check_inboxes(self):
        from ..models import Community, Message as MessageModel
        from ..config import Config

        communities = Community.query.all()
        inboxes = set()

        for c in communities:
            email = c.inbox_email or Config.AGENTMAIL_INBOX_ID
            inboxes.add(email)

        for inbox_email in inboxes:
            try:
                # List messages via REST API
                resp = requests.get(
                    f"{API_BASE}/inboxes/{inbox_email}/messages",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                messages = data.get("messages", [])

                for msg in messages:
                    msg_id = msg.get("message_id") or msg.get("id")
                    from_raw = msg.get("from", "") or ""
                    from_email = _parse_email(from_raw)

                    # Skip outbound messages (sent by us)
                    if from_email == inbox_email:
                        continue

                    if not from_email:
                        continue

                    # Check if we already processed this message
                    existing = MessageModel.query.filter_by(
                        agentmail_message_id=msg_id
                    ).first()

                    if existing:
                        continue

                    # Use preview from list, or fetch full message for body
                    body = msg.get("text") or msg.get("preview") or ""

                    if not body:
                        encoded_id = quote(msg_id, safe='')
                        detail_resp = requests.get(
                            f"{API_BASE}/inboxes/{inbox_email}/messages/{encoded_id}",
                            headers=self._headers(),
                        )
                        if detail_resp.ok:
                            detail = detail_resp.json()
                            body = detail.get("text") or detail.get("extracted_text") or detail.get("preview") or ""

                    if not body:
                        continue

                    to_list = msg.get("to", [])
                    to_email = to_list[0] if isinstance(to_list, list) and to_list else str(to_list)
                    subject = msg.get("subject", "")
                    thread_id = msg.get("thread_id")

                    print(f"  New email from {from_email}: {subject}", flush=True)

                    from .pipeline import process_inbound_email
                    process_inbound_email({
                        'from': from_email,
                        'to': to_email,
                        'subject': subject,
                        'body': body,
                        'message_id': msg_id,
                        'thread_id': thread_id,
                    })

            except Exception as e:
                print(f"  Poller error for {inbox_email}: {e}", flush=True)


# Global poller instance
poller = EmailPoller()
