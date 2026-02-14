import sys
import os
import pytest

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import create_app
from backend.app.extensions import db as _db
from backend.app.models import Organization, User, Community, Tenant, Document, Conversation, Message


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret'
    EMAIL_INTAKE_MODE = 'webhook'  # prevent poller from starting
    OPENAI_API_KEY = 'test-key'
    COHERE_API_KEY = 'test-key'
    AGENTMAIL_API_KEY = 'test-key'
    AGENTMAIL_INBOX_ID = 'test@agentmail.to'
    AGENTMAIL_WEBHOOK_SECRET = ''
    OPERATOR_EMAIL = ''
    UPLOAD_FOLDER = '/tmp/replivo-test-uploads'


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        # Create only the tables we need (skip DocumentChunk which requires pgvector)
        for model in [Organization, User, Community, Tenant, Document, Conversation, Message]:
            model.__table__.create(_db.engine, checkfirst=True)
        yield app
        _db.session.remove()


@pytest.fixture()
def db(app):
    yield _db
    _db.session.rollback()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seed_data(db):
    """Create org, community, and tenant for tests."""
    org = Organization(id='org-1', name='Test Org', slug='test-org')
    db.session.add(org)
    db.session.flush()

    community = Community(
        id='comm-1', organization_id='org-1',
        name='Test Community', slug='test-community',
        inbox_email='test@replivo.example.com',
        settings={'auto_reply_enabled': False},
    )
    db.session.add(community)
    db.session.flush()

    tenant = Tenant(
        id='tenant-1', community_id='comm-1',
        name='Alice', email='alice@example.com', is_active=True,
    )
    db.session.add(tenant)

    user = User(id='user-1', organization_id='org-1',
                email='admin@test.com', username='admin')
    user.set_password('password')
    db.session.add(user)

    db.session.commit()

    return {'org': org, 'community': community, 'tenant': tenant, 'user': user}
