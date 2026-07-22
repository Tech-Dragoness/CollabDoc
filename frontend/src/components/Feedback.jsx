// frontend/src/components/Feedback.jsx
// Central place for toasts and confirmation dialogs, replacing the
// browser's native alert()/confirm() with UI that matches the app.
import { createContext, useCallback, useContext, useRef, useState } from "react";

const FeedbackContext = createContext(null);

export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [confirmState, setConfirmState] = useState(null);
  const idRef = useRef(0);

  const showToast = useCallback((message, type = "success") => {
    const id = ++idRef.current;
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 3500);
  }, []);

  const confirm = useCallback((message, opts = {}) => {
    return new Promise((resolve) => {
      setConfirmState({ message, danger: !!opts.danger, resolve });
    });
  }, []);

  function resolveConfirm(result) {
    confirmState?.resolve(result);
    setConfirmState(null);
  }

  return (
    <FeedbackContext.Provider value={{ showToast, confirm }}>
      {children}

      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>{t.message}</div>
        ))}
      </div>

      {confirmState && (
        <div className="modal-backdrop" onClick={() => resolveConfirm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{confirmState.danger ? "Please confirm" : "Confirm"}</h2>
            <p style={{ fontSize: 14, color: "var(--muted)" }}>{confirmState.message}</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => resolveConfirm(false)}>Cancel</button>
              <button
                className={confirmState.danger ? "btn-danger" : "btn"}
                onClick={() => resolveConfirm(true)}
              >
                {confirmState.danger ? "Yes, continue" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  return useContext(FeedbackContext);
}