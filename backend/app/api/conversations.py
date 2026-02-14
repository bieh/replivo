import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, current_app
from ..extensions import db
from ..models import Conversation, Message, User

bp = Blueprint('conversations', __name__)


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route('', methods=['GET'])
def list_conversations():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    query = Conversation.query

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    community_id = request.args.get('community_id')
    if community_id:
        query = query.filter_by(community_id=community_id)

    conversations = query.order_by(Conversation.updated_at.desc()).all()

    result = []
    for conv in conversations:
        d = conv.to_dict()
        # Include community name and last message preview
        if conv.community:
            d['community_name'] = conv.community.name
        if conv.tenant:
            d['tenant_name'] = conv.tenant.name
        last_msg = conv.messages.order_by(Message.created_at.desc()).first()
        if last_msg:
            d['last_message_preview'] = last_msg.body_text[:200] if last_msg.body_text else ''
        result.append(d)

    return jsonify(result)


@bp.route('/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    conv = Conversation.query.get_or_404(conversation_id)
    d = conv.to_dict()
    d['messages'] = [m.to_dict() for m in conv.messages.order_by(Message.created_at).all()]
    if conv.community:
        d['community_name'] = conv.community.name
    if conv.tenant:
        d['tenant_name'] = conv.tenant.name
        d['tenant_unit'] = conv.tenant.unit
    return jsonify(d)


@bp.route('/<conversation_id>/approve', methods=['POST'])
def approve_conversation(conversation_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    conv = Conversation.query.get_or_404(conversation_id)

    # Find the AI draft message
    draft = conv.messages.filter_by(direction='outbound', is_ai_generated=True).first()
    if not draft:
        return jsonify({'error': 'No draft to approve'}), 400

    # Generate citation token and URL
    token = uuid.uuid4().hex[:12]
    draft.citation_token = token
    citation_url = f"{current_app.config['FRONTEND_URL'].rstrip('/')}/citations/{token}"

    # Send via AgentMail
    from ..services.email_service import send_reply
    try:
        send_reply(conv, draft.body_text, citation_url=citation_url)
    except Exception as e:
        return jsonify({'error': f'Failed to send: {e}'}), 500

    draft.sent_at = datetime.now(timezone.utc)
    conv.status = 'replied'
    db.session.commit()
    return jsonify(conv.to_dict())


@bp.route('/<conversation_id>/edit-and-send', methods=['POST'])
def edit_and_send(conversation_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    conv = Conversation.query.get_or_404(conversation_id)
    data = request.get_json()
    body = data.get('body', '')

    # Generate citation token and URL
    token = uuid.uuid4().hex[:12]
    citation_url = f"{current_app.config['FRONTEND_URL'].rstrip('/')}/citations/{token}"

    # Send via AgentMail
    from ..services.email_service import send_reply
    try:
        send_reply(conv, body, citation_url=citation_url)
    except Exception as e:
        return jsonify({'error': f'Failed to send: {e}'}), 500

    # Create outbound message record
    msg = Message(
        conversation_id=conv.id,
        direction='outbound',
        from_email=conv.community.inbox_email or 'replivo@agentmail.to',
        to_email=conv.sender_email,
        subject=f"Re: {conv.subject}",
        body_text=body,
        is_ai_generated=False,
        citation_token=token,
        sent_at=datetime.now(timezone.utc),
    )
    db.session.add(msg)
    conv.status = 'replied'
    db.session.commit()
    return jsonify(conv.to_dict())


@bp.route('/<conversation_id>/reply', methods=['POST'])
def manual_reply(conversation_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    conv = Conversation.query.get_or_404(conversation_id)
    data = request.get_json()
    body = data.get('body', '')

    from ..services.email_service import send_reply
    try:
        send_reply(conv, body)
    except Exception as e:
        return jsonify({'error': f'Failed to send: {e}'}), 500

    msg = Message(
        conversation_id=conv.id,
        direction='outbound',
        from_email=conv.community.inbox_email or 'replivo@agentmail.to',
        to_email=conv.sender_email,
        subject=f"Re: {conv.subject}",
        body_text=body,
        is_ai_generated=False,
        sent_at=datetime.now(timezone.utc),
    )
    db.session.add(msg)
    conv.status = 'replied'
    db.session.commit()
    return jsonify(conv.to_dict())


@bp.route('/<conversation_id>/close', methods=['POST'])
def close_conversation(conversation_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    conv = Conversation.query.get_or_404(conversation_id)
    conv.status = 'closed'
    db.session.commit()
    return jsonify(conv.to_dict())
