# Architecture Note — CollabDoc

## Stack
- **Frontend:** React + Vite, `react-router-dom` for routing, `react-quill`
  for the rich-text editor, `axios` for API calls.
- **Backend:** Flask, `Flask-SQLAlchemy` as the ORM, `Flask-JWT-Extended` for
  stateless auth, `bcrypt` for password hashing.
- **Database:** PostgreSQL, six tables: `users`, `documents`,
  `document_shares`, `comments`, `document_access_log`, `attachments`.

## What was prioritized, and why

**1. Correctness of the sharing/permission model over feature breadth.**
Every document route resolves access through a single helper
(`get_document_or_403` + `resolve_access`) that checks: is this user the
owner, or is there a `document_shares` row for them, or neither. Access is
now a 4-level hierarchy (`view` < `comment` < `edit` < `collaborator`), and
every route that needs a given capability checks against one of three
shared sets (`EDIT_ACCESS`, `COMMENT_ACCESS`, `FULL_ACCESS`) rather than
re-deriving the logic per route — the most common way collaborative-doc
demos break is checking auth correctly in one route but not another.
`collaborator` is deliberately defined as "in `FULL_ACCESS` alongside
`owner`," not as a separately-implemented set of permissions, so the two
can't silently drift out of sync.

**2. Stateless auth (JWT) over server-side sessions.**
Keeps the backend a plain, horizontally-scalable HTTP API with no session
store, which matches a simple Render deployment and how the React SPA
talks to it (bearer token, no cookie/CORS-credentials complexity).

**3. Explicit, small file-import surface over "accept anything."**
Import-to-document stays a small whitelist (`.txt`, `.md`, `.docx`)
converted via well-known libraries, with the limitation stated in-app.
Attachments genuinely accept any file type since they're only ever stored
and downloaded, never parsed or rendered.

**4. Server-side validation, not just client-side.**
Password/email regexes and the permission-hierarchy checks all live in
`app.py`, since a determined user or a second client could bypass
client-only checks.

**5. Autosave with debounce over an explicit "Save" button.**
One `PUT` endpoint handles both title and content updates; it also stamps
`last_edited_by_id` so "who last edited this, and when" can be shown
without a separate versioning system.

**6. The access log is a simple open-event audit trail, not version control.**
"Who accessed what and when" was interpreted literally per the spec: a
`document_access_log` row per open, with no ability to view or restore
prior content — building real version history (diffs, restores) would be
a materially bigger feature than what was asked for. An earlier version
of this also tried to record when each session closed (via a tab-close
beacon), but that added complexity without adding anything the spec
asked for, and a crashed/force-closed tab could never reliably report a
close anyway — so it was simplified back down to just the open event.

## Deliberate simplifications (given "don't over-engineer")
- No real-time collaborative editing (no CRDT/OT) — each save is a full
  snapshot; concurrent edits are last-write-wins.
- No password reset / email verification flow.
- File imports and PDF export run synchronously in the request; fine at
  this scale, would move to a background job for large files/scale.