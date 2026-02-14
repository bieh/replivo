import uuid
from flask import Blueprint, request, jsonify, session
from ..extensions import db
from ..models import User, Message, Conversation
from ..config import Config

bp = Blueprint('playground', __name__)


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route('/ask', methods=['POST'])
def playground_ask():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    community_id = data.get('community_id')
    question = data.get('question', '').strip()
    conversation_history = data.get('conversation_history')

    if not community_id:
        return jsonify({'error': 'community_id is required'}), 400
    if not question:
        return jsonify({'error': 'question is required'}), 400

    from ..services.pipeline import process_question
    result = process_question(community_id, question,
                              conversation_history=conversation_history)

    # Generate a citation token so playground answers have a linkable citation page
    token = uuid.uuid4().hex[:12]
    citation_url = f"{Config.FRONTEND_URL.rstrip('/')}/citations/{token}"

    # Find or create a playground conversation to attach the message to
    conv = Conversation.query.filter_by(
        community_id=community_id, sender_email='playground'
    ).first()
    if not conv:
        conv = Conversation(
            community_id=community_id,
            subject='Playground',
            status='auto_replied',
            sender_email='playground',
        )
        db.session.add(conv)
        db.session.flush()

    msg = Message(
        conversation_id=conv.id,
        direction='outbound',
        from_email='playground',
        to_email='playground',
        subject=question[:200],
        body_text=result['answer_text'],
        citations=result['citations'],
        ai_response_data=result['raw_response'],
        is_ai_generated=True,
        citation_token=token,
    )
    db.session.add(msg)
    db.session.commit()

    result['citation_url'] = citation_url
    return jsonify(result)
