# AI Workflow Note — CollabDoc

This file is a running log of the AI-assisted workflow used to build
CollabDoc. Each entry below corresponds to one conversation/session and is
appended, never edited or removed, once written.

---

## Entry 1 — 22 July 2026, IST

Prior sessions (summarized from uploaded artifacts, not directly logged
here) had already produced the backend (Flask app with auth, document
CRUD, sharing, and file-import endpoints; SQLAlchemy models; a Postgres
`setup.sql` schema; a passing pytest suite) and most of the frontend
(auth context, API client, Login/Signup/Dashboard/Editor React
components, and shared CSS), organized as a `CollabDoc` project with a
`frontend/` folder and backend files at the project root.

This session's work:
- Reorganized the backend files into a `CollabDoc/backend/` subfolder
  (matching what `test_app.py`'s own docstring already assumed: `cd
  backend && pytest -v`), and verified the whole test suite (8 tests)
  actually installs and passes cleanly in a fresh virtual environment.
- Found and fixed a real bug: the auth context file had been saved as
  `Authcontext.jsx` (lowercase "c") while every component that imports it
  uses `../api/AuthContext` (capital "C"). This is invisible on
  case-insensitive filesystems (Mac/Windows) but breaks the build on
  Linux, which is what Render (and most CI) uses — renamed the file to
  `AuthContext.jsx` to match.
- The uploaded `App.jsx` was still Vite's default starter template
  (counter button, Vite/React logos) rather than the real application
  shell. Replaced it with the actual app: a `BrowserRouter` wiring
  `/login`, `/signup`, `/` (Dashboard), and `/documents/:id` (Editor),
  wrapped in `AuthProvider`, with a `PrivateRoute` guard redirecting
  unauthenticated users to `/login`.
- Added the frontend files that hadn't been generated yet so the project
  actually builds and runs: `main.jsx` (React entry point), `index.html`,
  `package.json` (with `react-router-dom`, `react-quill`, `axios`, Vite +
  the React plugin as dependencies), and `vite.config.js`.
- Filled in the previously-empty `frontend/.env` with
  `VITE_API_URL=http://localhost:5000` for local dev, and added a
  `backend/.env.example` template (documenting `DATABASE_URL`,
  `JWT_SECRET_KEY`, `UPLOAD_FOLDER`) since no real backend `.env` existed
  yet and the real one shouldn't be committed to git.
- Added a root `.gitignore` (venv, `__pycache__`, `node_modules`,
  `dist`, both real `.env` files, uploaded attachments folder).
- Wrote `README.md` (setup/run instructions for DB, backend, frontend,
  and tests), `ARCHITECTURE.md` (this project's design priorities and
  trade-offs), `DEPLOYMENT.md` (GitHub + Render step-by-step), and
  `SUBMISSION.md` (full file listing), and this AI workflow file.

---

## Entry 2 — 22 July 2026, IST (same-day follow-up)

This session addressed five bugs/gaps found during user testing of the
live app:
- **Double-spaced imported documents**: traced to the `markdown` library
  emitting real newline characters between HTML block tags (e.g.
  `<p>Hello</p>\n<h2>...</h2>`); Quill's HTML parser was interpreting that
  whitespace as an extra blank paragraph. Fixed by collapsing
  insignificant inter-tag whitespace in `file_import.py`'s `.md`/`.docx`
  converters, plus a defensive normalize-on-load in `Editor.jsx`.
- **No viewer/editor distinction on shares**: the `DocumentShare.permission`
  column already existed in the schema but was never surfaced. Wired it
  through: the share modal now has a "Can edit" / "Can view only" selector,
  `POST /share` accepts and upserts a permission, `GET /documents/:id`
  returns the caller's resolved permission, and both `PUT /documents/:id`
  and attachment uploads now reject edits from view-only users. The
  editor renders the Quill toolbar as read-only and hides the toolbar
  entirely for viewers.
- **Images silently dropped**: `.docx` import only ever walked paragraph
  text runs, so inline images were ignored with no error. Now extracts
  each run's embedded image via its relationship ID and inlines it as a
  base64 `<img>` tag. Also added a real image button to the editor
  toolbar (client-side base64 embed, 3MB cap) since there was previously
  no way to insert an image directly in the editor at all.
- **No color/font controls**: added `color`, `background`, and `font`
  to the Quill toolbar and formats list.
- **Plain UI**: reworked `App.css` — Inter typeface, gradient accents,
  hover/lift transitions on cards and buttons, softer shadows, and a
  fade-in on modals and page loads. No component structure changes were
  needed for this.

Not touched this session (not part of the uploaded file set, so unverified
here): `setup.sql`, `DEPLOYMENT.md`, `SUBMISSION.md`,
`WALKTHROUGH_VIDEO.txt`, `requirements.txt`, `package.json`, and the Vite
scaffold files. These were reported as created in Entry 1 but weren't part
of this review batch — worth double-checking they're still present and
current in the actual repo.

**Known limitation carried forward, not fixed this session:** embedded
video and Quill's `formula`/`video` embeds aren't wired up — only images,
links, and text formatting. If video embedding is needed, that's a
follow-up.

---

## Entry 3 — 22 July 2026, IST (later same-day follow-up)

This session addressed seven items from a second round of user testing:

- **Editing a shared doc's permission**: added `PATCH
  /documents/:id/share/:user_id`, and an inline permission dropdown +
  "Update" button on each row of the "Shared with" panel in `Editor.jsx`,
  so an existing share no longer has to be removed and re-added to change
  its access level.
- **Success feedback on sharing/permission changes**: replaced ad hoc
  handling with a toast system (`components/Feedback.jsx`). Sharing a doc
  with someone new shows "Document shared with X."; updating an existing
  share (via either the share modal re-sharing to the same email, or the
  new inline "Update" control) shows "Permission updated for X."; removing
  access shows a matching toast too.
- **Better alert/confirmation UI**: `Feedback.jsx` also adds a promise-based
  `confirm()` modal styled to match the rest of the app, replacing the
  browser's native `window.confirm` for document deletion and for the new
  collaborator-permission warning below. Plain `alert()` was never used in
  this codebase, so no other replacements were needed.
- **Comments + comment-only access**: added a `Comment` model, `GET`/`POST
  /documents/:id/comments`, and a comments panel in the editor. Access is
  now a 4-level hierarchy (`view` < `comment` < `edit` < `collaborator`):
  `view` can't edit or comment; `comment` can comment but the document body
  is read-only for them; `edit` can do both; the editor's read-only state
  (`readOnly`) is now driven by this hierarchy rather than a boolean.
- **Collaborator access level**: added `collaborator` as a share permission
  with the same rights as the owner (edit, share, delete, export, access
  log) — implemented as a single `FULL_ACCESS = {"owner", "collaborator"}`
  check used everywhere those actions are gated, both so it can't drift out
  of sync and so it's obvious in the code that these two levels are meant
  to be equivalent. Both the share modal and the inline permission editor
  show a confirmation warning before an account is set to `collaborator`.
- **PDF/Markdown export**: added `GET /documents/:id/export?format=pdf|md`.
  Markdown uses the `html2text` library; PDF uses `xhtml2pdf` (pure-Python,
  no system-level dependencies, which matters for a simple Render deploy).
  Export is available to the owner always, and to a shared user only when
  their access is `collaborator`, per spec — enforced with the same
  `require_full` check used for delete and share management.
- **Edit attribution + access log**: `Document` gained a
  `last_edited_by_id` column, set whenever `PUT /documents/:id` changes the
  title or content; the editor now shows "Last edited by X on <timestamp>"
  under the title. Separately, added a `DocumentAccessLog` table (one row
  per open/close session) and `POST /access/open`, `POST /access/close`,
  and `GET /access-log` endpoints. The editor opens a log entry on mount
  and closes it (recording the close timestamp, per the spec's requirement
  that this is "the timestamp of when they closed the doc") both on route
  navigation away and on tab close, the latter via a `fetch(..., {keepalive:
  true})` call in a `beforeunload` handler since a normal axios call isn't
  reliable during page unload. A new `AccessLog.jsx` page, linked from the
  editor and visible only to the owner/collaborator, lists this history.
  This is explicitly a read-only audit trail, not version history — no
  endpoint allows restoring old content, matching the spec.

Also added `migration_v2.sql` as a **separate** file (not merged into
`setup.sql`) so an already-deployed database can be updated in place
(`ALTER TABLE` for the new column, `CREATE TABLE IF NOT EXISTS` for the two
new tables) without re-running the full fresh-install schema. `setup.sql`
itself was updated in parallel so fresh installs get the same final schema
directly. `requirements.txt` gained `html2text` and `xhtml2pdf` for export.
`test_app.py` grew from 8 to 12 tests, covering permission updates,
comment-only/view-only comment restrictions, and collaborator rights.

**Not touched this session:** `DEPLOYMENT.md`'s core steps (still accurate
as written); `package.json`/Vite scaffold (no new frontend dependencies
were needed — comments, export, and the access log all reuse the existing
`client.js`/axios setup).

---
 
## Entry 4 — 22 July 2026, IST (further same-day follow-up)
 
This session addressed two issues from live user testing:
 
- **Growing blank space around lists on every edit/reload**: the previous
  fix only stripped whitespace *between* HTML tags on import and on
  initial document load. It didn't account for Quill itself inserting an
  empty `<p><br></p>` immediately before and after list blocks during
  normal editing (needed for cursor placement inside the editor) — each
  load-edit-save cycle let another one accumulate, which is what made the
  gap visibly grow over repeated opens. Added a `normalizeContent()`
  helper in `Editor.jsx` that strips those empty paragraphs adjacent to
  `<ul>`/`<ol>` blocks (in addition to the existing whitespace collapse),
  now applied both on load and before every autosave, so the extra
  paragraphs never make it into what's persisted. Also added the same
  normalization server-side in `app.py` (`normalize_content`, applied on
  both document creation and `PUT /documents/:id`) as a defensive
  backstop, independent of the frontend.
- **Access log showed "Still open / not recorded" for sessions that never
  got a close beacon**: simplified the access log to match what was
  actually asked for — "who opened the document and when" — rather than
  an open/close session model. Removed the `closed_at` column from
  `DocumentAccessLog`/`document_access_log`, removed the
  `POST /documents/:id/access/close` route and the corresponding
  `beforeunload`/tab-close beacon in `Editor.jsx`, and updated
  `AccessLog.jsx` to show only a "User" and "Opened" column. `setup.sql`
  was updated so fresh installs no longer create the column, and a new
  `migration_v3.sql` was added (separate from `migration_v2.sql`) to drop
  `closed_at` from databases that already have it. `README.md` and
  `ARCHITECTURE.md` were updated to describe the access log as opens-only.
**Not touched this session:** `test_app.py` (existing access-log test only
checks the endpoint returns 200, so it still passes unchanged);
`DEPLOYMENT.md`; `package.json`/Vite scaffold.