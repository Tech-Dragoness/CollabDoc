# Deployment Guide — GitHub + Render

This deploys the **backend** (Flask API + Postgres) and **frontend** (React
static site) on Render, with the source pushed to GitHub first.

## Part A — Push to GitHub

```bash
cd CollabDoc
git init
git add .
git commit -m "Initial CollabDoc submission"
```
Create a new empty repo on github.com (no README/license, so it stays
empty), then:
```bash
git remote add origin https://github.com/<your-username>/CollabDoc.git
git branch -M main
git push -u origin main
```

## Part B — Create the Postgres database on Render

1. Go to https://dashboard.render.com → **New** → **PostgreSQL**.
2. Name it `collabdoc-db`, choose a region, leave defaults, click
   **Create Database**.
3. Once it's up, open it and copy the **Internal Database URL** (starts
   with `postgresql://`). You'll paste this into the backend service's
   env vars in Part C.
4. Run the schema against it. Render gives you an **External Database
   URL** too (needed since you're connecting from your own machine) — use
   that one for this one-time step:
   ```bash
   cd CollabDoc/backend
   psql "<EXTERNAL_DATABASE_URL>" -f setup.sql
   ```

## Part C — Deploy the backend on Render

1. Dashboard → **New** → **Web Service** → connect your GitHub repo.
2. Configure:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
3. Add environment variables (Render service → **Environment**):
   - `DATABASE_URL` = the **Internal Database URL** from Part B
   - `JWT_SECRET_KEY` = a long random string (generate with
     `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `UPLOAD_FOLDER` = `uploads`
4. Click **Create Web Service**. Once deployed, note the URL, e.g.
   `https://collabdoc-backend.onrender.com`. Confirm it's alive:
   ```bash
   curl https://collabdoc-backend.onrender.com/api/health
   ```

   > Note: attachment files saved to disk on Render's free tier don't
   > persist across deploys/restarts (ephemeral filesystem). Fine for a
   > demo; for production use a persistent disk or object storage (e.g.
   > S3) for the `UPLOAD_FOLDER`.

## Part D — Deploy the frontend on Render

1. Dashboard → **New** → **Static Site** → connect the same GitHub repo.
2. Configure:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
3. Add environment variable:
   - `VITE_API_URL` = your backend URL from Part C, e.g.
     `https://collabdoc-backend.onrender.com`
4. Under **Redirects/Rewrites**, add a rewrite rule so client-side routing
   works on refresh:
   - Source: `/*` → Destination: `/index.html` → Action: **Rewrite**
5. Click **Create Static Site**. Once deployed, this URL (e.g.
   `https://collabdoc-frontend.onrender.com`) is your live product URL.

## Part E — Sanity check the live deployment

1. Open the frontend URL, sign up with a real-looking email/password.
2. Create a document, type some formatted text, refresh — confirm it
   persisted.
3. Sign up a second account (different browser/incognito), share the
   first document with its email, confirm it shows under "Shared with
   you" for the second account.
