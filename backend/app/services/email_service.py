"""AgentMail REST API wrapper for sending emails."""
import re
import requests
import markdown
from ..config import Config

API_BASE = "https://api.agentmail.to/v0"


def _headers():
    return {
        "Authorization": f"Bearer {Config.AGENTMAIL_API_KEY}",
        "Content-Type": "application/json",
    }


def markdown_to_html(text: str) -> str:
    """Convert markdown text to a styled HTML email body."""
    body_html = markdown.markdown(text, extensions=['extra', 'sane_lists'])
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #374151; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
{body_html}
</body>
</html>"""


def _linkify_citations(text: str, citation_url: str) -> str:
    """Replace [N] patterns with markdown links to citation anchors."""
    def replace_cite(m):
        n = m.group(1)
        return f"[[{n}]]({citation_url}#cite-{n})"
    return re.sub(r'\[(\d+)\]', replace_cite, text)


def send_reply(conversation, body_text: str, citation_url: str = None):
    """Send a reply via AgentMail REST API."""
    try:
        inbox_id = conversation.community.inbox_email or Config.AGENTMAIL_INBOX_ID

        full_text = body_text
        if citation_url:
            full_text = _linkify_citations(full_text, citation_url)
            full_text += f"\n\n---\n[View all sources]({citation_url})"

        html_body = markdown_to_html(full_text)

        payload = {
            "to": [conversation.sender_email],
            "subject": f"Re: {conversation.subject}",
            "text": full_text,
            "html": html_body,
        }

        resp = requests.post(
            f"{API_BASE}/inboxes/{inbox_id}/messages/send",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        print(f"  Sent reply to {conversation.sender_email}")
    except Exception as e:
        print(f"  Email send error: {e}")
        raise
