-- ============================================================
-- Document App: PostgreSQL schema setup
--
-- Run with (from a terminal, after creating the database/user):
--   psql -U docapp_user -d docapp -f setup.sql
--
-- See README.md "Database setup" section for the full sequence
-- of commands including creating the role/database first.
--
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id                SERIAL PRIMARY KEY,
    owner_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title             VARCHAR(255) NOT NULL DEFAULT 'Untitled Document',
    content           TEXT NOT NULL DEFAULT '',
    last_edited_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- permission: 'view' | 'comment' | 'edit' | 'collaborator'
--   view         - read only, no comments, no edits
--   comment      - read + comment, no content edits
--   edit         - read + comment + edit content
--   collaborator - full owner-equivalent rights (edit, share, delete, export, access log)
CREATE TABLE IF NOT EXISTS document_shares (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission  VARCHAR(20) NOT NULL DEFAULT 'edit',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Read-only audit trail: one row per time a user opens a document. No old
-- content is ever recoverable from this table.
CREATE TABLE IF NOT EXISTS document_access_log (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opened_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attachments (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    filename    VARCHAR(255) NOT NULL,
    filepath    VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents(owner_id);
CREATE INDEX IF NOT EXISTS idx_shares_document_id ON document_shares(document_id);
CREATE INDEX IF NOT EXISTS idx_shares_user_id ON document_shares(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_document_id ON comments(document_id);
CREATE INDEX IF NOT EXISTS idx_access_log_document_id ON document_access_log(document_id);
CREATE INDEX IF NOT EXISTS idx_access_log_user_id ON document_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_attachments_document_id ON attachments(document_id);

-- Note: the Flask app also calls db.create_all() on startup as a convenience
-- fallback (useful for quick local runs), but this file is the source of
-- truth for the schema and is what you should run against a fresh database,
-- including in production on Render.