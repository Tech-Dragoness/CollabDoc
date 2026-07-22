import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../api/AuthContext";
import client, { extractError } from "../api/client";

function permLabel(p) {
  return (
    {
      view: "Viewer",
      comment: "Comment only",
      edit: "Editor",
      collaborator: "Collaborator",
    }[p] || p
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [docs, setDocs] = useState({ owned: [], shared: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  async function load() {
    setLoading(true);
    try {
      const { data } = await client.get("/documents");
      setDocs(data);
    } catch (err) {
      setError(extractError(err, "Could not load documents."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createBlank() {
    setError("");
    try {
      const { data } = await client.post("/documents", {
        title: "Untitled Document",
      });
      navigate(`/documents/${data.id}`);
    } catch (err) {
      setError(extractError(err, "Could not create document."));
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await client.post("/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/documents/${data.id}`);
    } catch (err) {
      setError(extractError(err, "Could not import file."));
    }
  }

  return (
    <div>
      <div className="topbar">
        <div
          className="brand"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "1.25rem",
            fontWeight: "bold",
          }}
        >
          <img
            src="./src/assets/Logo.png"
            alt="Logo"
            style={{
              height: "32px",
              width: "32px",
              objectFit: "contain",
            }}
          />
          <span>CollabDoc</span>
        </div>
        <div>
          <span className="user-email">{user?.email}</span>
          <button className="btn-secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      <div className="page-body">
        <div className="dash-header">
          <h2 style={{ margin: 0 }}>Your documents</h2>
          <div className="dash-actions">
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              accept=".txt,.md,.markdown,.docx"
              onChange={handleFileUpload}
            />
            <button
              className="btn-secondary"
              onClick={() => fileInputRef.current.click()}
            >
              Upload &amp; import file
            </button>
            <button className="btn" onClick={createBlank}>
              + New document
            </button>
          </div>
        </div>

        {error && <div className="error-box">{error}</div>}

        {loading ? (
          <p className="empty-state">Loading...</p>
        ) : (
          <>
            <div className="section-title">
              Owned by you ({docs.owned.length})
            </div>
            {docs.owned.length === 0 ? (
              <p className="empty-state">
                No documents yet. Create one to get started.
              </p>
            ) : (
              <div className="doc-grid">
                {docs.owned.map((d) => (
                  <DocCard key={d.id} doc={d} badge="owned" />
                ))}
              </div>
            )}

            <div className="section-title">
              Shared with you ({docs.shared.length})
            </div>
            {docs.shared.length === 0 ? (
              <p className="empty-state">
                Nothing has been shared with you yet.
              </p>
            ) : (
              <div className="doc-grid">
                {docs.shared.map((d) => (
                  <DocCard key={d.id} doc={d} badge="shared" />
                ))}
              </div>
            )}
          </>
        )}

        <p className="hint" style={{ marginTop: 30 }}>
          Supported file imports: .txt, .md, .docx. Other file types are not
          converted into documents.
        </p>
      </div>
    </div>
  );
}

function DocCard({ doc, badge }) {
  return (
    <Link className="doc-card" to={`/documents/${doc.id}`}>
      <span className={`badge ${badge}`}>
        {badge === "owned" ? "Owned" : `Shared by ${doc.owner_email}`}
      </span>
      {badge === "shared" && (
        <span
          className={`perm-badge ${doc.permission}`}
          style={{ marginLeft: 6 }}
        >
          {permLabel(doc.permission)}
        </span>
      )}
      <div className="title">{doc.title}</div>
      <div className="meta">
        Updated {new Date(doc.updated_at).toLocaleString()}
      </div>
    </Link>
  );
}
