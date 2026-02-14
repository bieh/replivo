import re

import requests
from flask import Blueprint, request, jsonify, current_app

bp = Blueprint('webhooks', __name__)


def _parse_email(raw: str) -> str:
    """Extract bare email from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', raw)
    return match.group(1) if match else raw.strip()


@bp.route('/agentmail', methods=['POST'])
def agentmail_webhook():
    """Receive inbound email events from AgentMail webhook."""
    # Verify webhook signature if configured
    webhook_secret = current_app.config.get('AGENTMAIL_WEBHOOK_SECRET')
    if webhook_secret:
        try:
            from svix.webhooks import Webhook
            wh = Webhook(webhook_secret)
            headers = {
                'svix-id': request.headers.get('svix-id', ''),
                'svix-timestamp': request.headers.get('svix-timestamp', ''),
                'svix-signature': request.headers.get('svix-signature', ''),
            }
            wh.verify(request.get_data(as_text=True), headers)
        except Exception:
            return jsonify({'error': 'Invalid signature'}), 401

    payload = request.get_json()

    # AgentMail webhook payload has the message at top level or under "data"
    msg = payload.get('data', payload)

    from_raw = msg.get('from', '') or ''
    from_email = _parse_email(from_raw)
    to_list = msg.get('to', [])
    to_email = to_list[0] if isinstance(to_list, list) and to_list else str(to_list)

    # Get body — may need to fetch full message via API
    body = msg.get('text') or msg.get('preview') or ''

    if not body and msg.get('message_id'):
        # Fetch full message from API
        from ..config import Config
        inbox_id = msg.get('inbox_id', to_email)
        api_key = Config.AGENTMAIL_API_KEY
        try:
            from urllib.parse import quote
            encoded_id = quote(msg['message_id'], safe='')
            resp = requests.get(
                f"https://api.agentmail.to/v0/inboxes/{inbox_id}/messages/{encoded_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.ok:
                detail = resp.json()
                body = detail.get('text') or detail.get('extracted_text') or detail.get('preview') or ''
        except Exception as e:
            current_app.logger.error(f"Failed to fetch message body: {e}")

    if not body:
        return jsonify({'ok': True, 'skipped': 'no body'})

    email_data = {
        'from': from_email,
        'to': to_email,
        'subject': msg.get('subject', ''),
        'body': body,
        'message_id': msg.get('message_id'),
        'thread_id': msg.get('thread_id'),
    }

    from ..services.pipeline import process_inbound_email
    try:
        result = process_inbound_email(email_data)
        return jsonify({'ok': True, 'status': result.get('status')})
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': str(e)}), 500
