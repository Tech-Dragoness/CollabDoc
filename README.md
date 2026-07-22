# CollabDoc

A small full-stack collaborative document editor: sign up, create rich-text
documents, import files into them, attach files, comment on them, and share
documents with other users by email — with view, comment, edit, or full
collaborator access.

- **Frontend:** React (Vite) + `react-quill` for rich text
- **Backend:** Python (Flask) + SQLAlchemy
- **Database:** PostgreSQL

```
CollabDoc/
├── backend/            Flask API
│   ├── app.py
│   ├── config.py
│   ├── file_import.py
│   ├── models.py
│   ├── requirements.txt
│   ├── setup.sql        <- run this to create the database schema
│   ├── test_app.py
│   └── .env.example      <- copy to .env and fill in
└── frontend/           React app (Vite)
    ├── src/
    │   ├── api/          AuthContext.jsx, client.js
    │   ├── components/   Login.jsx, Signup.jsx, Feedback.jsx
    │   ├── pages/         Dashboard.jsx, Editor.jsx, AccessLog.jsx
    │   ├── App.jsx, main.jsx, App.css
    └── .env               <- VITE_API_URL
```

---

## 1. Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL 14+ running locally (or a connection string to a hosted one)

Check what you have:
```bash
python --version
node --version
psql --version
```

---

## 2. Database setup (PostgreSQL)

Create a role and database (skip if you already have one you want to reuse):

```bash
sudo -u postgres psql
```
Inside the `psql` prompt:
```sql
CREATE USER docapp_user WITH PASSWORD 'docapp_pass';
CREATE DATABASE docapp OWNER docapp_user;
\q
```

Now create the tables using the provided schema file — run this **exact command**
from the `backend/` folder:

```bash
psql -U docapp_user -d docapp -h localhost -f setup.sql
```

(You'll be prompted for the password: `docapp_pass`, or whatever you set above.)

This creates `users`, `documents`, `document_shares`, and `attachments` tables.
The Flask app also calls `db.create_all()` on startup as a safety net, but
`setup.sql` is the source of truth and what you should run against a fresh
database.

---

## 3. Backend setup

```bash
cd CollabDoc/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create your local environment file:
```bash
cp .env.example .env
```
Then open `.env` and set:
```
DATABASE_URL=postgresql://docapp_user:docapp_pass@localhost:5432/docapp
JWT_SECRET_KEY=<generate one, see below>
UPLOAD_FOLDER=uploads
```
Generate a real secret instead of using a placeholder:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run the backend:
```bash
python app.py
```
It starts on `http://localhost:5000`. Check it's alive:
```bash
curl http://localhost:5000/api/health
# {"status":"ok"}
```

---

## 4. Frontend setup

In a **second terminal**:
```bash
cd CollabDoc/frontend
npm install
```

Check `.env` in `frontend/` points at your backend (this is already set for
local dev, no change needed unless your backend runs on a different port):
```
VITE_API_URL=http://localhost:5000
```

Run the frontend:
```bash
npm run dev
```
Open the URL it prints (usually `http://localhost:5173`).

---

## 5. Using the app

1. Sign up (password: 8+ chars, a letter, a number, a special character).
2. Create a blank document or import a `.txt` / `.md` / `.docx` file.
3. Edit with the rich-text toolbar; changes autosave ~0.7s after typing.
4. **Share** a document you own or collaborate on, and choose an access
   level:
   - **View only** — read only, no comments, no edits.
   - **Comment only** — can add comments, can't edit the content.
   - **Editor** — can edit content and comment.
   - **Collaborator** — full owner-equivalent rights: edit, share, delete,
     export, and view the access log. A confirmation warning appears
     before you can grant this.
   You can change an existing share's permission at any time from the
   "Shared with" panel — no need to remove and re-add them.
5. **Comments** — anyone with comment, edit, collaborator, or owner access
   can leave comments in the side panel; view-only users can't.
6. **Export** — owners and collaborators can export a document to PDF or
   Markdown from the editor toolbar.
7. **Access log** — owners and collaborators can see a full history of who
   opened the document and when, via the "Access log" link in the editor.
   This is a read-only audit trail — it does not let you restore old
   content.
8. Attach any file type to a document from the editor's side panel (view
   and comment-only access are read-only for attachments too).

**Supported file-to-document imports:** `.txt`, `.md`/`.markdown`, `.docx`
only, stated in the UI and here. **Attachments** accept any file type.

---

## 6. Running the automated tests

```bash
cd CollabDoc/backend
source venv/bin/activate
pytest -v
```
You should see **12 passing tests** covering auth validation, document
CRUD, file import, sharing/permission resolution (including the new
permission-update endpoint), comment-only and view-only comment
restrictions, and collaborator rights.

---

## 7. Deployment, architecture notes, and other deliverables

See these files in the project root:
- `DEPLOYMENT.md` — step-by-step GitHub + Render deployment instructions
- `ARCHITECTURE.md` — short architecture note
- `AI_WORKFLOW.md` — running log of the AI-assisted workflow for this project
- `SUBMISSION.md` — list of everything included in this submission
- `WALKTHROUGH_VIDEO.txt` — link to the walkthrough video