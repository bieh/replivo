import uuid
from datetime import datetime, timezone
from ..extensions import db


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    agentmail_message_id = db.Column(db.String(255), nullable=True)
    direction = db.Column(db.String(20), nullable=False)  # 'inbound' or 'outbound'
    from_email = db.Column(db.String(255), nullable=False)
    to_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), default='')
    body_text = db.Column(db.Text, default='')
    body_html = db.Column(db.Text, nullable=True)
    citations = db.Column(db.JSON, nullable=True)
    ai_response_data = db.Column(db.JSON, nullable=True)  # full structured LLM output
    is_ai_generated = db.Column(db.Boolean, default=False)
    citation_token = db.Column(db.String(12), unique=True, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'direction': self.direction,
            'from_email': self.from_email,
            'to_email': self.to_email,
            'subject': self.subject,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'citations': self.citations,
            'ai_response_data': self.ai_response_data,
            'is_ai_generated': self.is_ai_generated,
            'citation_token': self.citation_token,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
