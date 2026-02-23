import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

const initialRegister = {
  username: "",
  email: "",
  full_name: "",
  password: "",
  password_confirm: "",
};

export default function AuthPage({ mode = "login" }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(
    mode === "login" ? { username: "alex", password: "password123" } : initialRegister,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  function validate() {
    const next = {};
    if (!form.username?.trim()) next.username = "Required";
    if (!form.password || form.password.length < 8) next.password = "Min 8 chars";
    if (mode === "register") {
      if (!form.email?.trim()) next.email = "Required";
      if (!form.email?.includes("@")) next.email = "Invalid email";
      if (!form.password_confirm) next.password_confirm = "Required";
      if (form.password !== form.password_confirm) next.password_confirm = "Passwords do not match";
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        await auth.login({ username: form.username.trim(), password: form.password });
      } else {
        await auth.register({
          username: form.username.trim(),
          email: form.email.trim().toLowerCase(),
          full_name: form.full_name.trim(),
          password: form.password,
          password_confirm: form.password_confirm,
        });
      }
      navigate("/boards");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(typeof e.payload === "object" ? "Check form fields and try again." : e.message);
        if (e.payload && typeof e.payload === "object") setFieldErrors(e.payload);
      } else {
        setError("Request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-glow auth-glow-a" />
      <div className="auth-glow auth-glow-b" />
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <p className="eyebrow">MiniTrello</p>
        <h1>{mode === "login" ? "Welcome back" : "Create account"}</h1>
        <p className="auth-subtitle">
          {mode === "login" ? "JWT-based sign in for your training board." : "Register a new user and start planning tasks."}
        </p>

        <label>
          Username
          <input name="username" value={form.username} onChange={onChange} />
          {fieldErrors.username ? <span className="field-error">{String(fieldErrors.username)}</span> : null}
        </label>

        {mode === "register" ? (
          <>
            <label>
              Email
              <input name="email" type="email" value={form.email} onChange={onChange} />
              {fieldErrors.email ? <span className="field-error">{String(fieldErrors.email)}</span> : null}
            </label>
            <label>
              Full name
              <input name="full_name" value={form.full_name} onChange={onChange} />
            </label>
          </>
        ) : null}

        <label>
          Password
          <input name="password" type="password" value={form.password} onChange={onChange} />
          {fieldErrors.password ? <span className="field-error">{String(fieldErrors.password)}</span> : null}
        </label>

        {mode === "register" ? (
          <label>
            Confirm password
            <input name="password_confirm" type="password" value={form.password_confirm} onChange={onChange} />
            {fieldErrors.password_confirm ? (
              <span className="field-error">{String(fieldErrors.password_confirm)}</span>
            ) : null}
          </label>
        ) : null}

        {error ? <div className="form-alert">{error}</div> : null}

        <button className="btn btn-primary" disabled={loading}>
          {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Register"}
        </button>

        <p className="muted small">
          {mode === "login" ? "No account yet?" : "Already registered?"}{" "}
          <Link to={mode === "login" ? "/register" : "/login"}>
            {mode === "login" ? "Create one" : "Sign in"}
          </Link>
        </p>
        <p className="muted tiny">Seed users after backend seed: `alex` / `maria`, password `password123`.</p>
      </form>
    </div>
  );
}
