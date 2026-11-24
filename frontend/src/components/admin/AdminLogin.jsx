import { useState } from "react";
import {
  GraduationCap,
  Eye,
  EyeOff,
  LockKeyhole,
  User,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  LoaderCircle
} from "lucide-react";

import "./admin.css";

const API = "http://127.0.0.1:5000/api/admin";

export default function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          username: username.trim(),
          password
        })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.error || "Invalid administrator credentials."
        );
      }

      if (!result.access_token || !result.admin) {
        throw new Error("Invalid authentication response.");
      }

      sessionStorage.setItem(
        "campus_admin_token",
        result.access_token
      );

      sessionStorage.setItem(
        "campus_admin_user",
        JSON.stringify(result.admin)
      );

      onLogin?.({
        token: result.access_token,
        admin: result.admin
      });

    } catch (err) {
      setError(err.message || "Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="admin-login-page">

      <section className="admin-login-brand">
        <div className="admin-brand-logo">
          <GraduationCap size={34} />
        </div>

        <h1>CampusHelpDesk</h1>
        <p>University Administration Portal</p>

        <div className="admin-brand-message">
          <ShieldCheck size={22} />
          <span>Secure Administrator Access</span>
        </div>
      </section>

      <section className="admin-login-container">

        <div className="admin-login-card">

          <div className="admin-login-heading">
            <span className="admin-heading-icon">
              <LockKeyhole size={25} />
            </span>

            <h2>Administrator Login</h2>

            <p>
              Sign in to access your administration dashboard.
            </p>
          </div>

          {error && (
            <div className="admin-login-error" role="alert">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin}>

            <div className="admin-form-group">
              <label htmlFor="admin-username">
                Username
              </label>

              <div className="admin-input-wrapper">
                <User size={19} />

                <input
                  id="admin-username"
                  type="text"
                  placeholder="Enter administrator username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            <div className="admin-form-group">
              <label htmlFor="admin-password">
                Password
              </label>

              <div className="admin-input-wrapper">
                <LockKeyhole size={19} />

                <input
                  id="admin-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />

                <button
                  type="button"
                  className="admin-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={
                    showPassword ? "Hide password" : "Show password"
                  }
                >
                  {showPassword
                    ? <EyeOff size={19} />
                    : <Eye size={19} />
                  }
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="admin-login-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <LoaderCircle size={19} className="admin-spinner" />
                  Authenticating...
                </>
              ) : (
                <>
                  Sign In to Dashboard
                  <ArrowRight size={19} />
                </>
              )}
            </button>

          </form>

          <div className="admin-login-security">
            <ShieldCheck size={17} />
            <span>Protected Administrator Authentication</span>
          </div>

        </div>

        <p className="admin-login-footer">
          © {new Date().getFullYear()} CampusHelpDesk.
          All rights reserved.
        </p>

      </section>

    </main>
  );
}
