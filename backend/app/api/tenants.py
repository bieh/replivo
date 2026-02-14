from flask import Blueprint, request, jsonify, session
from ..extensions import db
from ..models import Tenant, User

bp = Blueprint('tenants', __name__)


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route('/communities/<community_id>/tenants', methods=['GET'])
def list_tenants(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    tenants = Tenant.query.filter_by(community_id=community_id).order_by(Tenant.name).all()
    return jsonify([t.to_dict() for t in tenants])


@bp.route('/communities/<community_id>/tenants', methods=['POST'])
def create_tenant(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()
    tenant = Tenant(
        community_id=community_id,
        name=data['name'],
        email=data['email'],
        unit=data.get('unit'),
    )
    db.session.add(tenant)
    db.session.commit()
    return jsonify(tenant.to_dict()), 201


@bp.route('/communities/<community_id>/tenants/<tenant_id>', methods=['PUT'])
def update_tenant(community_id, tenant_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    tenant = Tenant.query.get_or_404(tenant_id)
    data = request.get_json()
    if 'name' in data:
        tenant.name = data['name']
    if 'email' in data:
        tenant.email = data['email']
    if 'unit' in data:
        tenant.unit = data['unit']
    if 'is_active' in data:
        tenant.is_active = data['is_active']
    db.session.commit()
    return jsonify(tenant.to_dict())


@bp.route('/communities/<community_id>/tenants/<tenant_id>', methods=['DELETE'])
def delete_tenant(community_id, tenant_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    tenant = Tenant.query.get_or_404(tenant_id)
    db.session.delete(tenant)
    db.session.commit()
    return jsonify({'ok': True})
