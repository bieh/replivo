from flask import jsonify


def register_blueprints(app):
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.route('/api/admin/reset-db', methods=['POST'])
    def admin_reset_db():
        """Clear messages/conversations and re-process all documents."""
        import os
        secret = app.config.get('SECRET_KEY', '')
        from flask import request as req
        if req.headers.get('X-Admin-Key') != secret:
            return jsonify({'error': 'unauthorized'}), 403

        from ..extensions import db
        from ..models import Message, Conversation, Document, DocumentChunk

        # Clear messages and conversations
        msg_count = Message.query.count()
        conv_count = Conversation.query.count()
        Message.query.delete()
        Conversation.query.delete()
        db.session.commit()

        # Re-process all documents
        results = []
        docs = Document.query.filter_by(status='ready').all()
        for doc in docs:
            DocumentChunk.query.filter_by(document_id=doc.id).delete()
            db.session.commit()
            try:
                from ..services.document_service import process_document
                process_document(doc.id)
                chunk_count = DocumentChunk.query.filter_by(document_id=doc.id).count()
                results.append({'doc': doc.filename, 'chunks': chunk_count, 'status': 'ok'})
            except Exception as e:
                results.append({'doc': doc.filename, 'error': str(e)})

        return jsonify({
            'messages_deleted': msg_count,
            'conversations_deleted': conv_count,
            'documents_reprocessed': results,
        })

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
