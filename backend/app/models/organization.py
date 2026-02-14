import uuid
from datetime import datetime, timezone
from ..extensions import db


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    settings = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = db.relationship('User', backref='organization', lazy='dynamic')
    communities = db.relationship('Community', backref='organization', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
