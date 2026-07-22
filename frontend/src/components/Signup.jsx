import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../api/AuthContext";
import { extractError } from "../api/client";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup(email, password);
      navigate("/");
    } catch (err) {
      setError(extractError(err, "Sign up failed."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Create an account</h1>
        <p className="subtitle">Start writing and sharing documents</p>
        {error && <div className="error-box">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <p className="hint">
              At least 8 characters, with a letter, a number, and a special character (e.g. Passw0rd!23).
            </p>
          </div>
          <button className="btn" style={{ width: "100%" }} disabled={loading}>
            {loading ? "Creating account..." : "Sign up"}
          </button>
        </form>
        <p className="hint">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}