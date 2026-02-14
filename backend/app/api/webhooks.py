from flask import Blueprint, request, jsonify, current_app

bp = Blueprint('webhooks', __name__)


@bp.route('/agentmail', methods=['POST'])
def agentmail_webhook():
    """Receive inbound email events from AgentMail via Svix webhook."""
    # Verify webhook signature
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

    data = request.get_json()

    from ..services.pipeline import process_inbound_email
    try:
        process_inbound_email(data)
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'ok': True})
