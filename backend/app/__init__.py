import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from .config import Config
from .extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    frontend_url = app.config.get('FRONTEND_URL', 'http://localhost:5173')
    CORS(app, supports_credentials=True, origins=[frontend_url, 'http://localhost:5173'])

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so they're registered with SQLAlchemy
    from .models import (  # noqa: F401
        Organization, User, Community, Tenant,
        Document, DocumentChunk, Conversation, Message,
    )

    # Register blueprints
    from .api import register_blueprints
    register_blueprints(app)

    # Start email poller
    if app.config.get('EMAIL_INTAKE_MODE') == 'poll':
        from .services.email_poller import poller
        poller.init_app(app)
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            poller.start()

    # Serve frontend static files in production
    static_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist')
    if os.path.isdir(static_dir):
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            if path.startswith('api/'):
                from flask import abort
                abort(404)
            full = os.path.join(static_dir, path)
            if path and os.path.isfile(full):
                return send_from_directory(static_dir, path)
            return send_from_directory(static_dir, 'index.html')

    return app
