from flask import Blueprint, jsonify
from ..models import Message

bp = Blueprint('citations', __name__)


@bp.route('/<token>', methods=['GET'])
def get_citation(token):
    """Public endpoint — no auth required."""
    msg = Message.query.filter_by(citation_token=token).first()
    if not msg:
        return jsonify({'error': 'Citation not found'}), 404

    conv = msg.conversation
    community_name = conv.community.name if conv.community else ''

    # Find the inbound message for the original question
    inbound = conv.messages.filter_by(direction='inbound').first()

    return jsonify({
        'question': inbound.body_text if inbound else '',
        'subject': conv.subject,
        'answer_text': msg.body_text,
        'citations': msg.citations or [],
        'community_name': community_name,
    })
