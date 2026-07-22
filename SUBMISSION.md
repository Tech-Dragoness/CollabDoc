# Submission Contents — CollabDoc

## Root
- `README.md` — local setup and run instructions
- `ARCHITECTURE.md` — architecture note
- `AI_WORKFLOW.md` — running AI-workflow log (appended to each session)
- `DEPLOYMENT.md` — GitHub + Render deployment steps
- `SUBMISSION.md` — this file
- `WALKTHROUGH_VIDEO.txt` — walkthrough video URL
- `migration_v2.sql` — one-time migration for already-deployed databases (adds
  comments, collaborator/comment access levels, edit-tracking, access log)
- `migration_v3.sql` — one-time migration for databases that already ran
  migration_v2 (drops the unused `closed_at` column now that the access log
  only records opens)
- `.gitignore`

## backend/  (Flask API)
- `app.py` — all routes: auth, documents, sharing, comments, export, access log, attachments
- `config.py` — env-driven configuration
- `models.py` — SQLAlchemy models (User, Document, DocumentShare, Comment, DocumentAccessLog, Attachment)
- `file_import.py` — `.txt` / `.md` / `.docx` → HTML conversion
- `requirements.txt` — Python dependencies
- `setup.sql` — Postgres schema for fresh installs (run with `psql -U docapp_user -d docapp -f setup.sql`)
- `test_app.py` — automated test suite (pytest, 12 tests)
- `.env.example` — template for required environment variables

## frontend/  (React + Vite)
- `index.html`
- `package.json`, `vite.config.js`
- `.env` — `VITE_API_URL` (local dev default included)
- `src/main.jsx` — React entry point
- `src/App.jsx` — router shell (Login/Signup/Dashboard/Editor/AccessLog routes, auth guard)
- `src/App.css` — shared styles
- `src/api/AuthContext.jsx` — auth state (login/signup/logout), stores JWT
- `src/api/client.js` — axios instance, attaches bearer token, error helper
- `src/components/Login.jsx`
- `src/components/Signup.jsx`
- `src/components/Feedback.jsx` — toast notifications and confirmation dialogs
- `src/pages/Dashboard.jsx` — owned/shared document lists, create, file-import
- `src/pages/Editor.jsx` — rich-text editor, autosave, sharing, comments, export, access tracking
- `src/pages/AccessLog.jsx` — who accessed the document and when (owner/collaborator only)

## Not included in this repo (provided separately)
- Live product URL: https://collab-doc-omega.vercel.app/login
- The walkthrough video file: https://drive.google.com/file/d/1RS33t4jXKnkj5j_YZSG7W5wLjRCOA-Ds/view?usp=sharing
-The google drive containing all relevant files: https://drive.google.com/drive/folders/1atwBrq77TsGlyQggB5wrPqN_A-j76_mf?usp=sharing
-The Github project link: https://github.com/tech-dragoness/collabdoc