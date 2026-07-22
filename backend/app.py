# backend/app.py
import os
import re
import io
import uuid

import bcrypt
import html2text
from xhtml2pdf import pisa
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from config import Config
from models import db, User, Document, DocumentShare, Attachment, Comment, DocumentAccessLog
from file_import import file_to_html, UnsupportedFileType, SUPPORTED_EXTENSIONS

def normalize_content(raw):
    """
    Strips the empty <p><br></p> paragraphs Quill leaves directly before/after
    list blocks, plus any stray whitespace between tags. Applied server-side
    on every save as a defensive backstop (the editor also normalizes on its
    end) so the gap can't silently grow over repeated edits.
    """
    if not raw:
        return raw
    cleaned = re.sub(r"(?:<p>(?:<br\s*/?>)?</p>\s*)+(?=<(?:ul|ol)\b)", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"(</(?:ul|ol)>)(?:\s*<p>(?:<br\s*/?>)?</p>)+", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    return cleaned.strip()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# at least 1 letter, 1 digit, 1 special char, 8+ chars total
PASSWORD_RE = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]).{8,}$"
)

# Access levels, from lowest to highest:
#   view          - read only, no comments, no edits
#   comment       - read + add comments, no content edits
#   edit          - read + comment + edit content, but no share management,
#                   delete, export, or access-log
#   collaborator  - everything the owner can do (edit, share, delete,
#                   export, access log) except that they can't be un-owned
VALID_SHARE_PERMISSIONS = {"view", "comment", "edit", "collaborator"}
EDIT_ACCESS = {"owner", "collaborator", "edit"}
COMMENT_ACCESS = {"owner", "collaborator", "edit", "comment"}
FULL_ACCESS = {"owner", "collaborator"}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app):
    # ---------- helpers ----------
    def error(message, status=400):
        return jsonify({"error": message}), status

    def resolve_access(doc, user_id):
        """Returns 'owner', 'collaborator', 'edit', 'comment', 'view', or None."""
        if doc.owner_id == user_id:
            return "owner"
        share = DocumentShare.query.filter_by(document_id=doc.id, user_id=user_id).first()
        return share.permission if share else None

    def get_document_or_403(doc_id, user_id, require_full=False):
        doc = db.session.get(Document, doc_id)
        if not doc:
            return None, error("Document not found", 404)
        access = resolve_access(doc, user_id)
        if access is None:
            return None, error("You don't have access to this document", 403)
        if require_full and access not in FULL_ACCESS:
            return None, error("Only the owner or a collaborator can do this", 403)
        return doc, None

    # ---------- auth ----------
    @app.post("/api/auth/signup")
    def signup():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not EMAIL_RE.match(email):
            return error("Please provide a valid email address.")
        if not PASSWORD_RE.match(password):
            return error(
                "Password must be at least 8 characters and include a letter, "
                "a number, and a special character."
            )
        if User.query.filter_by(email=email).first():
            return error("An account with this email already exists.", 409)

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        return jsonify({"token": token, "user": user.to_public_dict()}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return error("Invalid email or password.", 401)

        token = create_access_token(identity=str(user.id))
        return jsonify({"token": token, "user": user.to_public_dict()})

    # ---------- documents ----------
    @app.get("/api/documents")
    @jwt_required()
    def list_documents():
        user_id = int(get_jwt_identity())
        owned = Document.query.filter_by(owner_id=user_id).order_by(Document.updated_at.desc()).all()
        shares = (
            db.session.query(Document, DocumentShare.permission)
            .join(DocumentShare, DocumentShare.document_id == Document.id)
            .filter(DocumentShare.user_id == user_id)
            .order_by(Document.updated_at.desc())
            .all()
        )
        shared_data = []
        for doc, permission in shares:
            item = doc.to_dict(include_content=False)
            item["permission"] = permission
            shared_data.append(item)
        return jsonify(
            {
                "owned": [d.to_dict(include_content=False) for d in owned],
                "shared": shared_data,
            }
        )

    @app.post("/api/documents")
    @jwt_required()
    def create_document():
        user_id = int(get_jwt_identity())
        title = "Untitled Document"
        content = ""

        if "file" in request.files and request.files["file"].filename:
            f = request.files["file"]
            try:
                content = file_to_html(f.filename, f.stream)
            except UnsupportedFileType as e:
                return error(str(e), 415)
            title = os.path.splitext(f.filename)[0][:255]
        else:
            data = request.get_json(silent=True) or {}
            title = (data.get("title") or title)[:255]
            content = normalize_content(data.get("content", ""))

        doc = Document(owner_id=user_id, title=title, content=content)
        db.session.add(doc)
        db.session.commit()
        return jsonify(doc.to_dict()), 201

    @app.get("/api/documents/<int:doc_id>")
    @jwt_required()
    def get_document(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        return jsonify(
            doc.to_dict()
            | {
                "is_owner": doc.owner_id == user_id,
                "permission": resolve_access(doc, user_id),
            }
        )

    @app.put("/api/documents/<int:doc_id>")
    @jwt_required()
    def update_document(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        if resolve_access(doc, user_id) not in EDIT_ACCESS:
            return error("You don't have edit access to this document.", 403)
        data = request.get_json(silent=True) or {}
        changed = False
        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return error("Title cannot be empty.")
            doc.title = title[:255]
            changed = True
        if "content" in data:
            doc.content = normalize_content(data.get("content", ""))
            changed = True
        if changed:
            doc.last_edited_by_id = user_id
        db.session.commit()
        return jsonify(doc.to_dict())

    @app.delete("/api/documents/<int:doc_id>")
    @jwt_required()
    def delete_document(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        db.session.delete(doc)
        db.session.commit()
        return jsonify({"deleted": True})

    # ---------- sharing ----------
    @app.post("/api/documents/<int:doc_id>/share")
    @jwt_required()
    def share_document(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        permission = (data.get("permission") or "edit").strip().lower()
        if permission not in VALID_SHARE_PERMISSIONS:
            return error("Permission must be one of: view, comment, edit, collaborator.")

        target = User.query.filter_by(email=email).first()
        if not target:
            return error("No user with that email exists.", 404)
        if target.id == doc.owner_id:
            return error("You already own this document.")

        existing = DocumentShare.query.filter_by(document_id=doc_id, user_id=target.id).first()
        if existing:
            existing.permission = permission
            db.session.commit()
            return jsonify({"shared_with": email, "permission": permission, "updated": True})

        db.session.add(DocumentShare(document_id=doc_id, user_id=target.id, permission=permission))
        db.session.commit()
        return jsonify({"shared_with": email, "permission": permission, "updated": False}), 201

    @app.patch("/api/documents/<int:doc_id>/share/<int:target_user_id>")
    @jwt_required()
    def update_share_permission(doc_id, target_user_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        data = request.get_json(silent=True) or {}
        permission = (data.get("permission") or "").strip().lower()
        if permission not in VALID_SHARE_PERMISSIONS:
            return error("Permission must be one of: view, comment, edit, collaborator.")
        share = DocumentShare.query.filter_by(document_id=doc_id, user_id=target_user_id).first()
        if not share:
            return error("This document isn't shared with that user.", 404)
        share.permission = permission
        db.session.commit()
        return jsonify({"user_id": target_user_id, "email": share.user.email, "permission": permission})

    @app.get("/api/documents/<int:doc_id>/shares")
    @jwt_required()
    def list_shares(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        shares = DocumentShare.query.filter_by(document_id=doc_id).all()
        return jsonify(
            [{"user_id": s.user_id, "email": s.user.email, "permission": s.permission} for s in shares]
        )

    @app.delete("/api/documents/<int:doc_id>/share/<int:target_user_id>")
    @jwt_required()
    def unshare_document(doc_id, target_user_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        DocumentShare.query.filter_by(document_id=doc_id, user_id=target_user_id).delete()
        db.session.commit()
        return jsonify({"removed": True})

    # ---------- comments ----------
    @app.get("/api/documents/<int:doc_id>/comments")
    @jwt_required()
    def list_comments(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        items = Comment.query.filter_by(document_id=doc_id).order_by(Comment.created_at.asc()).all()
        return jsonify([c.to_dict() for c in items])

    @app.post("/api/documents/<int:doc_id>/comments")
    @jwt_required()
    def add_comment(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        if resolve_access(doc, user_id) not in COMMENT_ACCESS:
            return error("You don't have permission to comment on this document.", 403)
        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content:
            return error("Comment cannot be empty.")
        comment = Comment(document_id=doc_id, user_id=user_id, content=content[:4000])
        db.session.add(comment)
        db.session.commit()
        return jsonify(comment.to_dict()), 201

    # ---------- export ----------
    @app.get("/api/documents/<int:doc_id>/export")
    @jwt_required()
    def export_document(doc_id):
        user_id = int(get_jwt_identity())
        # Owner always allowed; a shared user only if they're a collaborator.
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        fmt = (request.args.get("format") or "pdf").strip().lower()
        safe_title = re.sub(r"[^A-Za-z0-9 _-]", "", doc.title).strip() or "document"

        if fmt == "md":
            converter = html2text.HTML2Text()
            converter.body_width = 0
            markdown_text = converter.handle(doc.content or "")
            buf = io.BytesIO(markdown_text.encode("utf-8"))
            return send_file(
                buf, mimetype="text/markdown", as_attachment=True,
                download_name=f"{safe_title}.md",
            )

        if fmt == "pdf":
            html_doc = f"<html><body>{doc.content or ''}</body></html>"
            buf = io.BytesIO()
            result = pisa.CreatePDF(io.StringIO(html_doc), dest=buf)
            if result.err:
                return error("Could not generate a PDF for this document.", 500)
            buf.seek(0)
            return send_file(
                buf, mimetype="application/pdf", as_attachment=True,
                download_name=f"{safe_title}.pdf",
            )

        return error("Format must be 'pdf' or 'md'.")

    # ---------- access log ----------
    @app.post("/api/documents/<int:doc_id>/access/open")
    @jwt_required()
    def open_access_log(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        log = DocumentAccessLog(document_id=doc_id, user_id=user_id)
        db.session.add(log)
        db.session.commit()
        return jsonify({"log_id": log.id}), 201

    @app.get("/api/documents/<int:doc_id>/access-log")
    @jwt_required()
    def get_access_log(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id, require_full=True)
        if err:
            return err
        entries = (
            DocumentAccessLog.query.filter_by(document_id=doc_id)
            .order_by(DocumentAccessLog.opened_at.desc())
            .all()
        )
        return jsonify([e.to_dict() for e in entries])

    # ---------- attachments ----------
    @app.post("/api/documents/<int:doc_id>/attachments")
    @jwt_required()
    def upload_attachment(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        if resolve_access(doc, user_id) not in EDIT_ACCESS:
            return error("You don't have edit access to this document.", 403)
        if "file" not in request.files or not request.files["file"].filename:
            return error("No file provided.")
        f = request.files["file"]
        stored_name = f"{uuid.uuid4().hex}_{f.filename}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        f.save(path)
        attachment = Attachment(document_id=doc_id, filename=f.filename, filepath=stored_name)
        db.session.add(attachment)
        db.session.commit()
        return jsonify(attachment.to_dict()), 201

    @app.get("/api/documents/<int:doc_id>/attachments")
    @jwt_required()
    def list_attachments(doc_id):
        user_id = int(get_jwt_identity())
        doc, err = get_document_or_403(doc_id, user_id)
        if err:
            return err
        items = Attachment.query.filter_by(document_id=doc_id).all()
        return jsonify([a.to_dict() for a in items])

    @app.get("/api/attachments/<int:attachment_id>/download")
    @jwt_required()
    def download_attachment(attachment_id):
        user_id = int(get_jwt_identity())
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return error("Attachment not found", 404)
        doc, err = get_document_or_403(attachment.document_id, user_id)
        if err:
            return err
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], attachment.filepath, as_attachment=True,
            download_name=attachment.filename,
        )

    @app.get("/api/meta/supported-file-types")
    def supported_file_types():
        return jsonify(sorted(SUPPORTED_EXTENSIONS))

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)