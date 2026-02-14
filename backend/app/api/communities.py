from flask import Blueprint, request, jsonify, session
from ..extensions import db
from ..models import Community, User

bp = Blueprint('communities', __name__)


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route('', methods=['GET'])
def list_communities():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    communities = Community.query.filter_by(organization_id=user.organization_id).order_by(Community.name).all()
    return jsonify([c.to_dict() for c in communities])


@bp.route('', methods=['POST'])
def create_community():
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()
    community = Community(
        organization_id=user.organization_id,
        name=data['name'],
        slug=data.get('slug', data['name'].lower().replace(' ', '-')),
        description=data.get('description', ''),
        inbox_email=data.get('inbox_email'),
        settings=data.get('settings', {'auto_reply_enabled': True}),
    )
    db.session.add(community)
    db.session.commit()
    return jsonify(community.to_dict()), 201


@bp.route('/<community_id>', methods=['GET'])
def get_community(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    community = Community.query.get_or_404(community_id)
    return jsonify(community.to_dict())


@bp.route('/<community_id>', methods=['PUT'])
def update_community(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    community = Community.query.get_or_404(community_id)
    data = request.get_json()
    if 'name' in data:
        community.name = data['name']
    if 'description' in data:
        community.description = data['description']
    if 'settings' in data:
        community.settings = data['settings']
    if 'inbox_email' in data:
        community.inbox_email = data['inbox_email']
    db.session.commit()
    return jsonify(community.to_dict())


@bp.route('/<community_id>', methods=['DELETE'])
def delete_community(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    community = Community.query.get_or_404(community_id)
    db.session.delete(community)
    db.session.commit()
    return jsonify({'ok': True})
