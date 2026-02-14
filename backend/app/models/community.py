import uuid
from datetime import datetime, timezone
from ..extensions import db


class Community(db.Model):
    __tablename__ = 'communities'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default='')
    inbox_email = db.Column(db.String(255), nullable=True)
    agentmail_inbox_id = db.Column(db.String(255), nullable=True)
    settings = db.Column(db.JSON, default=lambda: {'auto_reply_enabled': True})
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenants = db.relationship('Tenant', backref='community', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='community', lazy='dynamic', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='community', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'slug', name='uq_community_org_slug'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'inbox_email': self.inbox_email,
            'settings': self.settings,
            'tenant_count': self.tenants.count(),
            'document_count': self.documents.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
