from flask import Blueprint, jsonify, session
from sqlalchemy import func
from ..models import Conversation, Community, User

bp = Blueprint('dashboard', __name__)


@bp.route('/stats', methods=['GET'])
def stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    communities = Community.query.filter_by(organization_id=user.organization_id).all()
    community_ids = [c.id for c in communities]

    status_counts = dict(
        Conversation.query
        .filter(Conversation.community_id.in_(community_ids))
        .with_entities(Conversation.status, func.count(Conversation.id))
        .group_by(Conversation.status)
        .all()
    )

    recent = (
        Conversation.query
        .filter(Conversation.community_id.in_(community_ids))
        .filter(Conversation.status.in_(['draft_ready', 'needs_human']))
        .order_by(Conversation.updated_at.desc())
        .limit(10)
        .all()
    )

    inboxes = [
        {'community_name': c.name, 'inbox_email': c.inbox_email}
        for c in communities if c.inbox_email
    ]

    return jsonify({
        'status_counts': status_counts,
        'total': sum(status_counts.values()),
        'needs_attention': status_counts.get('draft_ready', 0) + status_counts.get('needs_human', 0),
        'recent': [c.to_dict() for c in recent],
        'inboxes': inboxes,
    })
