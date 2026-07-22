// frontend/src/pages/AccessLog.jsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import client, { extractError } from "../api/client";

export default function AccessLog() {
  const { id } = useParams();
  const [entries, setEntries] = useState([]);
  const [docTitle, setDocTitle] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [docRes, logRes] = await Promise.all([
          client.get(`/documents/${id}`),
          client.get(`/documents/${id}/access-log`),
        ]);
        setDocTitle(docRes.data.title);
        setEntries(logRes.data);
      } catch (err) {
        setError(
          extractError(err, "Could not load the access log. Only the owner or a collaborator can view it.")
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  return (
    <div>
      <div className="topbar">
        <Link to={`/documents/${id}`} className="brand" style={{ textDecoration: "none" }}>
          ← Back to document
        </Link>
      </div>
      <div className="page-body">
        <h2 style={{ marginTop: 0 }}>Access log — {docTitle}</h2>
        <p className="hint" style={{ marginBottom: 20 }}>
          Who opened this document and when. This is a read-only audit trail —
          it doesn't let you restore an earlier version of the content.
        </p>
        {error && <div className="error-box">{error}</div>}
        {loading ? (
          <p className="empty-state">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="empty-state">No access recorded yet.</p>
        ) : (
          <table className="access-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>{e.user_email}</td>
                  <td>{new Date(e.opened_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}