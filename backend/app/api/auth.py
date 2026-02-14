from flask import Blueprint, request, jsonify, session
from ..models import User

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id
    return jsonify(user.to_dict())


@bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'ok': True})


@bp.route('/me', methods=['GET'])
def me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(user.to_dict())
