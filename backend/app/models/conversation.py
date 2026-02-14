import uuid
from datetime import datetime, timezone
from ..extensions import db


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    community_id = db.Column(db.String(36), db.ForeignKey('communities.id'), nullable=False)
    tenant_id = db.Column(db.String(36), db.ForeignKey('tenants.id'), nullable=True)
    agentmail_thread_id = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(500), default='')
    status = db.Column(db.String(50), default='pending_review')
    sender_email = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan',
                               order_by='Message.created_at')

    __table_args__ = (
        db.Index('ix_conversation_community_status', 'community_id', 'status'),
        db.Index('ix_conversation_sender', 'sender_email'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'community_id': self.community_id,
            'tenant_id': self.tenant_id,
            'subject': self.subject,
            'status': self.status,
            'sender_email': self.sender_email,
            'agentmail_thread_id': self.agentmail_thread_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
