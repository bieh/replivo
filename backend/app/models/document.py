import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.types import UserDefinedType
from ..extensions import db

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class TSVector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self):
        return 'TSVECTOR'


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    community_id = db.Column(db.String(36), db.ForeignKey('communities.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), default='pdf')
    file_path = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, default=0)
    total_pages = db.Column(db.Integer, nullable=True)
    total_chunks = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    full_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='processing')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chunks = db.relationship('DocumentChunk', backref='document', lazy='dynamic', cascade='all, delete-orphan',
                             order_by='DocumentChunk.chunk_index')

    def to_dict(self):
        return {
            'id': self.id,
            'community_id': self.community_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'total_pages': self.total_pages,
            'total_chunks': self.total_chunks,
            'total_tokens': self.total_tokens,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DocumentChunk(db.Model):
    __tablename__ = 'document_chunks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    article_number = db.Column(db.String(50), nullable=True)
    article_title = db.Column(db.String(255), nullable=True)
    section_group = db.Column(db.String(255), nullable=True)
    section_number = db.Column(db.String(50), nullable=True)
    page_number = db.Column(db.Integer, nullable=True)
    token_count = db.Column(db.Integer, default=0)
    search_vector = db.Column(TSVector(), nullable=True)


# Add embedding column only when pgvector is available
if Vector:
    DocumentChunk.embedding = db.Column(Vector(1536), nullable=True)

    __table_args__ = (
        db.Index('ix_chunk_search_vector', 'search_vector', postgresql_using='gin'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'article_number': self.article_number,
            'article_title': self.article_title,
            'section_group': self.section_group,
            'section_number': self.section_number,
            'page_number': self.page_number,
            'token_count': self.token_count,
        }
