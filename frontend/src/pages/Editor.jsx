// frontend/src/pages/Editor.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import ReactQuill from "react-quill";
import "react-quill/dist/quill.snow.css";
import logo from "../assets/Logo.png";
import client, { extractError } from "../api/client";
import { useFeedback } from "../components/Feedback";

const MAX_IMAGE_BYTES = 3 * 1024 * 1024; // 3MB, since images are embedded as base64

const QUILL_FORMATS = [
  "header",
  "bold",
  "italic",
  "underline",
  "color",
  "background",
  "font",
  "list",
  "bullet",
  "link",
  "image",
];

// Quill inserts an empty <p><br></p> immediately before/after list blocks
// (needed for cursor placement in the editor), but that empty paragraph
// gets saved as real content. Since normalization only ran on load, each
// load -> tiny edit -> save cycle let another one pile up. Stripping them
// here, on BOTH load and before every save, means they never make it into
// what's persisted.
function normalizeContent(raw) {
  if (!raw) return raw;
  return raw
    .replace(/(?:<p>(?:<br\s*\/?>)?<\/p>\s*)+(?=<(?:ul|ol)\b)/gi, "")
    .replace(/(<\/(?:ul|ol)>)(?:\s*<p>(?:<br\s*\/?>)?<\/p>)+/gi, "$1")
    .replace(/>\s+</g, "><")
    .trim();
}

const EDIT_ACCESS = ["owner", "collaborator", "edit"];
const COMMENT_ACCESS = ["owner", "collaborator", "edit", "comment"];
const FULL_ACCESS = ["owner", "collaborator"];

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

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast, confirm } = useFeedback();

  const [doc, setDoc] = useState(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isOwner, setIsOwner] = useState(false);
  const [permission, setPermission] = useState("edit");
  const [saveStatus, setSaveStatus] = useState("Saved");
  const [error, setError] = useState("");

  const [attachments, setAttachments] = useState([]);

  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");

  const [shares, setShares] = useState([]);
  const [pendingPerm, setPendingPerm] = useState({});
  const [showShare, setShowShare] = useState(false);
  const [shareEmail, setShareEmail] = useState("");
  const [sharePermission, setSharePermission] = useState("edit");
  const [shareError, setShareError] = useState("");

  const saveTimer = useRef(null);
  const attachmentInputRef = useRef(null);
  const quillRef = useRef(null);

  const readOnly = !EDIT_ACCESS.includes(permission);
  const hasCommentRights = COMMENT_ACCESS.includes(permission);
  const isFullAccess = FULL_ACCESS.includes(permission);

  const loadDoc = useCallback(async () => {
    setError("");
    try {
      const { data } = await client.get(`/documents/${id}`);
      setDoc(data);
      setTitle(data.title);
      setContent(normalizeContent(data.content || ""));
      setIsOwner(data.is_owner);
      setPermission(data.permission || (data.is_owner ? "owner" : "edit"));
    } catch (err) {
      setError(extractError(err, "Could not load document."));
    }
  }, [id]);

  const loadAttachments = useCallback(async () => {
    try {
      const { data } = await client.get(`/documents/${id}/attachments`);
      setAttachments(data);
    } catch {
      // non-fatal
    }
  }, [id]);

  const loadComments = useCallback(async () => {
    try {
      const { data } = await client.get(`/documents/${id}/comments`);
      setComments(data);
    } catch {
      // non-fatal
    }
  }, [id]);

  const loadShares = useCallback(async () => {
    try {
      const { data } = await client.get(`/documents/${id}/shares`);
      setShares(data);
    } catch {
      // full-access-only endpoint; ignore if forbidden
    }
  }, [id]);

  useEffect(() => {
    loadDoc();
    loadAttachments();
    loadComments();
  }, [loadDoc, loadAttachments, loadComments]);

  useEffect(() => {
    if (isFullAccess) loadShares();
  }, [isFullAccess, loadShares]);

  // Records one access-log row every time the document is opened.
  useEffect(() => {
    client.post(`/documents/${id}/access/open`).catch(() => {
      // access logging shouldn't block using the document
    });
  }, [id]);

  function scheduleSave(nextTitle, nextContent) {
    if (readOnly) return;
    setSaveStatus("Saving...");
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        const { data } = await client.put(`/documents/${id}`, {
          title: nextTitle,
          content: nextContent,
        });
        setDoc((prev) => (prev ? { ...prev, ...data } : prev));
        setSaveStatus("Saved");
      } catch (err) {
        setSaveStatus("Could not save");
        setError(extractError(err, "Could not save document."));
      }
    }, 700);
  }

  function handleTitleChange(e) {
    if (readOnly) return;
    const value = e.target.value;
    setTitle(value);
    scheduleSave(value, content);
  }

  function handleContentChange(value) {
    if (readOnly) return;
    setContent(value);
    scheduleSave(title, normalizeContent(value));
  }

  async function handleDelete() {
    const ok = await confirm("Delete this document? This can't be undone.", {
      danger: true,
    });
    if (!ok) return;
    try {
      await client.delete(`/documents/${id}`);
      navigate("/");
    } catch (err) {
      setError(extractError(err, "Could not delete document."));
    }
  }

  async function handleShareSubmit(e) {
    e.preventDefault();
    setShareError("");
    if (sharePermission === "collaborator") {
      const ok = await confirm(
        `Collaborator access gives ${shareEmail || "this person"} all the same rights you have as owner — ` +
          "including editing, sharing, exporting, deleting, and viewing the access log. Continue?",
        { danger: true },
      );
      if (!ok) return;
    }
    try {
      const { data } = await client.post(`/documents/${id}/share`, {
        email: shareEmail,
        permission: sharePermission,
      });
      showToast(
        data.updated
          ? `Permission updated for ${shareEmail}.`
          : `Document shared with ${shareEmail}.`,
        "success",
      );
      setShareEmail("");
      setSharePermission("edit");
      loadShares();
    } catch (err) {
      setShareError(extractError(err, "Could not share document."));
    }
  }

  async function updateSharePermission(share) {
    const newPerm = pendingPerm[share.user_id] ?? share.permission;
    if (newPerm === share.permission) return;
    if (newPerm === "collaborator") {
      const ok = await confirm(
        `Collaborator access gives ${share.email} all the same rights you have as owner. Continue?`,
        { danger: true },
      );
      if (!ok) return;
    }
    try {
      await client.patch(`/documents/${id}/share/${share.user_id}`, {
        permission: newPerm,
      });
      showToast(`Permission updated for ${share.email}.`, "success");
      loadShares();
    } catch (err) {
      setError(extractError(err, "Could not update permission."));
    }
  }

  async function removeShare(userId) {
    const share = shares.find((s) => s.user_id === userId);
    try {
      await client.delete(`/documents/${id}/share/${userId}`);
      showToast(`Removed access for ${share?.email || "user"}.`, "success");
      loadShares();
    } catch (err) {
      setError(extractError(err, "Could not remove access."));
    }
  }

  async function handleAttachmentUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      await client.post(`/documents/${id}/attachments`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      loadAttachments();
    } catch (err) {
      setError(extractError(err, "Could not upload attachment."));
    }
  }

  async function downloadAttachment(att) {
    const { data } = await client.get(`/attachments/${att.id}/download`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = att.filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  async function submitComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await client.post(`/documents/${id}/comments`, {
        content: newComment.trim(),
      });
      setNewComment("");
      loadComments();
    } catch (err) {
      setError(extractError(err, "Could not post comment."));
    }
  }

  async function handleExport(format) {
    try {
      const { data } = await client.get(`/documents/${id}/export`, {
        params: { format },
        responseType: "blob",
      });
      const mime = format === "pdf" ? "application/pdf" : "text/markdown";
      const url = window.URL.createObjectURL(new Blob([data], { type: mime }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title || "document"}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(extractError(err, "Could not export document."));
    }
  }

  // Custom image handler: reads a local image file and embeds it as a
  // base64 data URI directly in the document content.
  function imageHandler() {
    const input = document.createElement("input");
    input.setAttribute("type", "file");
    input.setAttribute("accept", "image/*");
    input.click();
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      if (file.size > MAX_IMAGE_BYTES) {
        setError("Images must be under 3MB.");
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const quill = quillRef.current?.getEditor();
        if (!quill) return;
        const range = quill.getSelection(true) || { index: quill.getLength() };
        quill.insertEmbed(range.index, "image", reader.result, "user");
        quill.setSelection(range.index + 1);
      };
      reader.readAsDataURL(file);
    };
  }

  const modules = useMemo(
    () => ({
      toolbar: readOnly
        ? false
        : {
            container: [
              [{ header: [1, 2, 3, false] }],
              ["bold", "italic", "underline"],
              [{ color: [] }, { background: [] }],
              [{ font: [] }],
              [{ list: "ordered" }, { list: "bullet" }],
              ["link", "image"],
              ["clean"],
            ],
            handlers: { image: imageHandler },
          },
    }),
    [readOnly],
  );

  if (error && !doc) {
    return (
      <div className="page-body">
        <div className="error-box">{error}</div>
        <Link to="/">← Back to documents</Link>
      </div>
    );
  }

  if (!doc) return <div className="page-body">Loading...</div>;

  return (
    <div>
      <div className="topbar">
        <Link
          to="/"
          className="brand"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "1.25rem",
            fontWeight: "bold",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          <span>←</span>
          <img
            src={logo}
            alt="Logo"
            style={{
              height: "32px",
              width: "32px",
              objectFit: "contain",
              display: "block",
            }}
          />
          <span>CollabApp</span>
        </Link>
        <span className="save-status">
          {readOnly
            ? hasCommentRights
              ? "Comment only"
              : "View only"
            : saveStatus}
        </span>
      </div>

      <div className="page-body">
        {!isOwner && (
          <div className="readonly-banner">
            This document was shared with you by {doc.owner_email} — access
            level: {permLabel(permission)}
            {permission === "collaborator" && " (full owner-equivalent rights)"}
            {permission === "edit" && " (can edit and comment)"}
            {permission === "comment" && " (can't edit content)"}
            {permission === "view" && " (can't edit or comment)"}
          </div>
        )}
        {error && <div className="error-box">{error}</div>}

        <div className="editor-header">
          <input
            className="title-input"
            value={title}
            onChange={handleTitleChange}
            disabled={readOnly}
          />
          <div className="editor-actions">
            {isFullAccess && (
              <>
                <button
                  className="btn-secondary"
                  onClick={() => handleExport("md")}
                >
                  Export .md
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => handleExport("pdf")}
                >
                  Export PDF
                </button>
                <Link
                  className="btn-secondary"
                  to={`/documents/${id}/access-log`}
                >
                  Access log
                </Link>
                <button
                  className="btn-secondary"
                  onClick={() => setShowShare(true)}
                >
                  Share
                </button>
                <button className="btn-danger" onClick={handleDelete}>
                  Delete
                </button>
              </>
            )}
          </div>
        </div>

        {doc.last_edited_by_email && (
          <p className="hint" style={{ marginTop: -8, marginBottom: 14 }}>
            Last edited by {doc.last_edited_by_email} on{" "}
            {new Date(doc.updated_at).toLocaleString()}
          </p>
        )}

        <div className="editor-shell">
          <ReactQuill
            ref={quillRef}
            theme="snow"
            readOnly={readOnly}
            value={content}
            onChange={handleContentChange}
            modules={modules}
            formats={QUILL_FORMATS}
          />
        </div>

        <div className="side-panel">
          <div className="panel-box">
            <h3>Attachments</h3>
            {attachments.length === 0 && (
              <p className="empty-state" style={{ padding: 0 }}>
                No attachments yet.
              </p>
            )}
            {attachments.map((a) => (
              <div className="list-row" key={a.id}>
                <span>{a.filename}</span>
                <button
                  className="btn-secondary"
                  onClick={() => downloadAttachment(a)}
                >
                  Download
                </button>
              </div>
            ))}
            {!readOnly && (
              <div className="upload-row">
                <input
                  type="file"
                  ref={attachmentInputRef}
                  style={{ display: "none" }}
                  onChange={handleAttachmentUpload}
                />
                <button
                  className="btn-secondary"
                  onClick={() => attachmentInputRef.current.click()}
                >
                  Attach a file
                </button>
              </div>
            )}
          </div>

          <div className="panel-box">
            <h3>Comments</h3>
            <div className="comments-list">
              {comments.length === 0 && (
                <p className="empty-state" style={{ padding: 0 }}>
                  No comments yet.
                </p>
              )}
              {comments.map((c) => (
                <div className="comment-row" key={c.id}>
                  <div className="comment-meta">
                    {c.user_email} · {new Date(c.created_at).toLocaleString()}
                  </div>
                  <div className="comment-body">{c.content}</div>
                </div>
              ))}
            </div>
            {hasCommentRights ? (
              <form onSubmit={submitComment} className="comment-form">
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
                  rows={2}
                />
                <button className="btn-secondary" type="submit">
                  Comment
                </button>
              </form>
            ) : (
              <p className="hint" style={{ marginTop: 10 }}>
                You don't have permission to comment on this document.
              </p>
            )}
          </div>

          {isFullAccess && (
            <div className="panel-box">
              <h3>Shared with</h3>
              {shares.length === 0 && (
                <p className="empty-state" style={{ padding: 0 }}>
                  Not shared with anyone yet.
                </p>
              )}
              {shares.map((s) => (
                <div className="list-row share-row" key={s.user_id}>
                  <span>
                    {s.email}{" "}
                    <span className={`perm-badge ${s.permission}`}>
                      {permLabel(s.permission)}
                    </span>
                  </span>
                  <div className="share-row-actions">
                    <select
                      value={pendingPerm[s.user_id] ?? s.permission}
                      onChange={(e) =>
                        setPendingPerm((p) => ({
                          ...p,
                          [s.user_id]: e.target.value,
                        }))
                      }
                    >
                      <option value="view">Viewer</option>
                      <option value="comment">Comment only</option>
                      <option value="edit">Editor</option>
                      <option value="collaborator">Collaborator</option>
                    </select>
                    <button
                      className="btn-secondary"
                      onClick={() => updateSharePermission(s)}
                    >
                      Update
                    </button>
                    <button
                      className="btn-danger"
                      onClick={() => removeShare(s.user_id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showShare && (
        <div className="modal-backdrop" onClick={() => setShowShare(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Share this document</h2>
            {shareError && <div className="error-box">{shareError}</div>}
            <form onSubmit={handleShareSubmit}>
              <div className="field">
                <label>Recipient's email</label>
                <input
                  type="email"
                  value={shareEmail}
                  onChange={(e) => setShareEmail(e.target.value)}
                  placeholder="teammate@example.com"
                  required
                />
              </div>
              <div className="field">
                <label>Access level</label>
                <select
                  value={sharePermission}
                  onChange={(e) => setSharePermission(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                  }}
                >
                  <option value="view">Can view only</option>
                  <option value="comment">Can comment only</option>
                  <option value="edit">Can edit</option>
                  <option value="collaborator">
                    Collaborator (full access, same as owner)
                  </option>
                </select>
                {sharePermission === "collaborator" && (
                  <p className="hint" style={{ color: "#b91c1c" }}>
                    Collaborators get full owner-equivalent rights: editing,
                    sharing, exporting, deleting, and the access log.
                  </p>
                )}
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowShare(false)}
                >
                  Close
                </button>
                <button className="btn">Share</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}