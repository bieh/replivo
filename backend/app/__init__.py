from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, supports_credentials=True, origins=['http://localhost:5173'])

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

    # Start email poller in dev mode
    if app.config.get('EMAIL_INTAKE_MODE') == 'poll':
        from .services.email_poller import poller
        poller.init_app(app)
        # Only start in the main process (not in reloader child)
        import os
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            poller.start()

    return app
