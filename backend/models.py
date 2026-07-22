from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    def to_public_dict(self):
        return {"id": self.id, "email": self.email}


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="Untitled Document")
    content = db.Column(db.Text, default="")
    last_edited_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)

    owner = db.relationship("User", foreign_keys=[owner_id], backref="documents")
    last_edited_by = db.relationship("User", foreign_keys=[last_edited_by_id])

    def to_dict(self, include_content=True):
        data = {
            "id": self.id,
            "owner_id": self.owner_id,
            "owner_email": self.owner.email if self.owner else None,
            "title": self.title,
            "last_edited_by_email": self.last_edited_by.email if self.last_edited_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data["content"] = self.content
        return data


class DocumentShare(db.Model):
    __tablename__ = "document_shares"
    __table_args__ = (db.UniqueConstraint("document_id", "user_id", name="uq_document_user"),)

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # 'view' | 'comment' | 'edit' | 'collaborator' (collaborator = full owner-equivalent rights)
    permission = db.Column(db.String(20), nullable=False, default="edit")
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    user = db.relationship("User")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user.email if self.user else None,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentAccessLog(db.Model):
    """
    One row per time a user opens a document, so the access log page can show
    'who accessed what and when'. This is a read-only audit trail, not
    version history — rows are never edited and old content can't be
    restored from them.
    """
    __tablename__ = "document_access_log"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opened_at = db.Column(db.DateTime(timezone=True), default=now)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user.email if self.user else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }