import uuid
from datetime import datetime, timezone
from ..extensions import db


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    community_id = db.Column(db.String(36), db.ForeignKey('communities.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    conversations = db.relationship('Conversation', backref='tenant', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('community_id', 'email', name='uq_tenant_community_email'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'community_id': self.community_id,
            'name': self.name,
            'email': self.email,
            'unit': self.unit,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
