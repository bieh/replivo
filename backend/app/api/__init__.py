from flask import jsonify


def register_blueprints(app):
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    def _check_admin(req):
        secret = app.config.get('SECRET_KEY', '')
        return req.headers.get('X-Admin-Key') == secret

    @app.route('/api/admin/reset-db', methods=['POST'])
    def admin_reset_db():
        """Clear messages/conversations only (fast)."""
        from flask import request as req
        if not _check_admin(req):
            return jsonify({'error': 'unauthorized'}), 403

        from ..extensions import db
        from ..models import Message, Conversation

        msg_count = Message.query.count()
        conv_count = Conversation.query.count()
        Message.query.delete()
        Conversation.query.delete()
        db.session.commit()

        return jsonify({
            'messages_deleted': msg_count,
            'conversations_deleted': conv_count,
        })

    @app.route('/api/admin/reprocess-doc/<doc_id>', methods=['POST'])
    def admin_reprocess_doc(doc_id):
        """Re-process a single document (delete chunks, re-parse, re-embed)."""
        from flask import request as req
        if not _check_admin(req):
            return jsonify({'error': 'unauthorized'}), 403

        from ..extensions import db
        from ..models import Document, DocumentChunk

        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'error': 'not found'}), 404

        DocumentChunk.query.filter_by(document_id=doc.id).delete()
        db.session.commit()

        from ..services.document_service import process_document
        process_document(doc.id)

        chunk_count = DocumentChunk.query.filter_by(document_id=doc.id).count()
        return jsonify({'doc': doc.filename, 'chunks': chunk_count, 'status': 'ok'})

    @app.route('/api/admin/docs', methods=['GET'])
    def admin_list_docs():
        """List all documents with chunk counts."""
        from flask import request as req
        if not _check_admin(req):
            return jsonify({'error': 'unauthorized'}), 403

        from ..models import Document, DocumentChunk
        docs = Document.query.all()
        return jsonify([{
            'id': d.id, 'filename': d.filename, 'status': d.status,
            'chunks': DocumentChunk.query.filter_by(document_id=d.id).count(),
        } for d in docs])

    from .auth import bp as auth_bp
    from .communities import bp as communities_bp
    from .tenants import bp as tenants_bp
    from .documents import bp as documents_bp
    from .conversations import bp as conversations_bp
    from .webhooks import bp as webhooks_bp
    from .dashboard import bp as dashboard_bp
    from .playground import bp as playground_bp
    from .citations import bp as citations_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(communities_bp, url_prefix='/api/communities')
    app.register_blueprint(tenants_bp, url_prefix='/api')
    app.register_blueprint(documents_bp, url_prefix='/api')
    app.register_blueprint(conversations_bp, url_prefix='/api/conversations')
    app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(playground_bp, url_prefix='/api/playground')
    app.register_blueprint(citations_bp, url_prefix='/api/citations')
