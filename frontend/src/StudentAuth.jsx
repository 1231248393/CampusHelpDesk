import { useState } from "react";
import { GraduationCap, LockKeyhole, Eye, EyeOff, ArrowRight, UserRound, Mail } from "lucide-react";
import "./StudentAuth.css";

const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000").replace(/\/$/, "");

export default function StudentAuth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState({ full_name: "", email: "", roll_number: "", password: "" });

  function update(field, value) {
    setForm(current => ({ ...current, [field]: value }));
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setSuccess("");
    const registering = mode === "register";
    try {
      const payload = registering
        ? { ...form, roll_number: form.roll_number.trim().toUpperCase(), email: form.email.trim().toLowerCase() }
        : { roll_number: form.roll_number.trim().toUpperCase(), password: form.password };
      const response = await fetch(`${API_BASE}/api/student/${registering ? "register" : "login"}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `${registering ? "Registration" : "Login"} failed (${response.status})`);
      if (!result.access_token || !result.student) throw new Error("The server returned an incomplete authentication response.");
      onAuth(result);
    } catch (err) {
      setError(err.message || "Unable to connect to the CampusHelpDesk API.");
    } finally { setBusy(false); }
  }

  function switchMode(next) { setMode(next); setError(""); setSuccess(""); }

  return (
    <main className="student-auth-page">
      <section className="student-auth-brand">
        <div className="student-auth-mark"><GraduationCap size={30} /></div>
        <span className="student-auth-kicker">CAMPUS SUPPORT PLATFORM</span>
        <h1>CampusHelpDesk</h1>
        <p>Your campus. Your voice. Track every issue until it is resolved.</p>
        <div className="student-auth-promise"><LockKeyhole size={16} /> Private student accounts and complaint tracking</div>
      </section>
      <section className="student-auth-side">
        <div className="student-auth-card">
          <div className="student-auth-icon"><GraduationCap size={24} /></div>
          <span className="student-auth-eyebrow">STUDENT PORTAL</span>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="student-auth-subtitle">{mode === "login" ? "Sign in to submit and privately track your campus complaints." : "Register with your college details to start using CampusHelpDesk."}</p>
          <form onSubmit={submit} className="student-auth-form">
            {mode === "register" && <>
              <label htmlFor="student-full-name">Full name</label>
              <div className="student-auth-input"><UserRound size={17}/><input id="student-full-name" required maxLength={120} autoComplete="name" placeholder="Your full name" value={form.full_name} onChange={e => update("full_name", e.target.value)}/></div>
              <label htmlFor="student-email">College email</label>
              <div className="student-auth-input"><Mail size={17}/><input id="student-email" type="email" required maxLength={190} autoComplete="email" placeholder="name@college.edu" value={form.email} onChange={e => update("email", e.target.value)}/></div>
            </>}
            <label htmlFor="student-roll-number">College roll number</label>
            <div className="student-auth-input"><GraduationCap size={17}/><input id="student-roll-number" required maxLength={50} autoComplete="username" placeholder="Enter your college roll number" value={form.roll_number} onChange={e => update("roll_number", e.target.value)}/></div>
            <label htmlFor="student-password">Password</label>
            <div className="student-auth-input"><LockKeyhole size={17}/><input id="student-password" required type={showPassword ? "text" : "password"} minLength={6} maxLength={72} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder={mode === "login" ? "Enter your password" : "At least 8 characters"} value={form.password} onChange={e => update("password", e.target.value)}/><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div>
            {error && <div className="student-auth-error" role="alert">{error}</div>}
            {success && <div className="student-auth-success" role="status">{success}</div>}
            <button className="student-auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in to Student Portal" : "Create student account"}<ArrowRight size={17}/></button>
          </form>
          <p className="student-auth-security"><LockKeyhole size={14}/> Protected by server-side JWT authentication</p>
        </div>
        <small className="student-auth-footer">© {new Date().getFullYear()} CampusHelpDesk · Student Portal</small>
      </section>
    </main>
  );
}

