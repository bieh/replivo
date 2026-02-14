import os
from flask import Blueprint, request, jsonify, session, current_app, send_file
from ..extensions import db
from ..models import Document, User

bp = Blueprint('documents', __name__)


def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


@bp.route('/communities/<community_id>/documents', methods=['GET'])
def list_documents(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    docs = Document.query.filter_by(community_id=community_id).order_by(Document.created_at.desc()).all()
    return jsonify([d.to_dict() for d in docs])


@bp.route('/communities/<community_id>/documents', methods=['POST'])
def upload_document(community_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    filename = file.filename
    filepath = os.path.join(upload_dir, f"{community_id}_{filename}")
    file.save(filepath)

    file_type = 'pdf' if filename.lower().endswith('.pdf') else 'txt'

    doc = Document(
        community_id=community_id,
        filename=filename,
        file_type=file_type,
        file_path=filepath,
        file_size=os.path.getsize(filepath),
        status='processing',
    )
    db.session.add(doc)
    db.session.commit()

    # Trigger async processing
    from ..services.document_service import process_document
    try:
        process_document(doc.id)
    except Exception as e:
        doc.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500

    return jsonify(doc.to_dict()), 201


@bp.route('/communities/<community_id>/documents/<doc_id>', methods=['GET'])
def get_document(community_id, doc_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    doc = Document.query.get_or_404(doc_id)
    return jsonify(doc.to_dict())


@bp.route('/communities/<community_id>/documents/<doc_id>', methods=['DELETE'])
def delete_document(community_id, doc_id):
    user = require_auth()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    doc = Document.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'ok': True})


def _resolve_doc_path(doc):
    """Resolve the file path for a document, handling relative paths."""
    file_path = doc.file_path
    if not file_path:
        return None
    if not os.path.isabs(file_path):
        file_path = os.path.join(current_app.root_path, '..', file_path)
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        return None
    return file_path


@bp.route('/documents/<doc_id>/download', methods=['GET'])
def download_document(doc_id):
    """Public (unauthenticated) endpoint to download a document PDF."""
    doc = Document.query.get_or_404(doc_id)
    file_path = _resolve_doc_path(doc)
    if not file_path:
        return jsonify({'error': 'File not found'}), 404
    return send_file(file_path, as_attachment=True, download_name=doc.filename)


@bp.route('/documents/<doc_id>/view', methods=['GET'])
def view_document(doc_id):
    """Public endpoint to view a document inline (for PDF.js rendering)."""
    doc = Document.query.get_or_404(doc_id)
    file_path = _resolve_doc_path(doc)
    if not file_path:
        return jsonify({'error': 'File not found'}), 404
    return send_file(file_path, mimetype='application/pdf', as_attachment=False)
