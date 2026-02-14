from flask import Blueprint, request, jsonify, session
from ..models import User

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

    return jsonify(result)
