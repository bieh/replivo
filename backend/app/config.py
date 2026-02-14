import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql+psycopg2://paul@localhost/replivo')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    AGENTMAIL_API_KEY = os.getenv('AGENTMAIL_API_KEY')
    AGENTMAIL_INBOX_ID = os.getenv('AGENTMAIL_INBOX_ID', 'replivo@agentmail.to')
    AGENTMAIL_WEBHOOK_SECRET = os.getenv('AGENTMAIL_WEBHOOK_SECRET', '')
    OPERATOR_EMAIL = os.getenv('OPERATOR_EMAIL', '')

    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    EMAIL_INTAKE_MODE = os.getenv(
        'EMAIL_INTAKE_MODE',
        'poll' if os.getenv('FLASK_ENV', 'development') == 'development' else 'webhook'
    )

    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
