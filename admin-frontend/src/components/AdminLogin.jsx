import { useState } from 'react';
import { GraduationCap, ShieldCheck, LockKeyhole, User, Eye, EyeOff, ArrowRight, LoaderCircle, AlertCircle } from 'lucide-react';
import { API_BASE, ADMIN_TOKEN_KEY, ADMIN_USER_KEY } from '../api';

export default function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault(); setError(''); setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password })
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || 'Unable to sign in.');
      if (!result.access_token || !result.admin) throw new Error('The server returned an invalid login response.');
      sessionStorage.setItem(ADMIN_TOKEN_KEY, result.access_token);
      sessionStorage.setItem(ADMIN_USER_KEY, JSON.stringify(result.admin));
      onLogin(result.admin);
    } catch (err) { setError(err.message || 'Cannot connect to the CampusHelpDesk API.'); }
    finally { setLoading(false); }
  }

  return <main className="login-shell">
    <section className="login-brand">
      <div className="brand-mark"><GraduationCap size={34}/></div>
      <div className="brand-kicker">CAMPUS SUPPORT PLATFORM</div>
      <h1>CampusHelpDesk</h1>
      <p>Administrator workspace</p>
      <div className="secure-note"><ShieldCheck size={19}/> Secure administrator access</div>
    </section>
    <section className="login-side">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-icon"><LockKeyhole size={24}/></div>
        <div className="eyebrow">ADMINISTRATOR SIGN IN</div>
        <h2>Welcome back</h2>
        <p className="muted">Sign in with your administrator account to manage campus complaints.</p>
        {error && <div className="alert-error" role="alert"><AlertCircle size={18}/>{error}</div>}
        <label htmlFor="admin-username">Username</label>
        <div className="input-wrap"><User size={18}/><input id="admin-username" value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" placeholder="Administrator username" required /></div>
        <label htmlFor="admin-password">Password</label>
        <div className="input-wrap"><LockKeyhole size={18}/><input id="admin-password" type={showPassword?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" placeholder="Your password" required/><button className="eye-btn" type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button></div>
        <button className="sign-in-btn" type="submit" disabled={loading}>{loading?<><LoaderCircle className="spin" size={18}/> Signing in…</>:<>Sign in to Admin Portal <ArrowRight size={18}/></>}</button>
        <div className="login-foot"><ShieldCheck size={16}/> Protected by server-side JWT authentication</div>
      </form>
      <div className="copyright">© {new Date().getFullYear()} CampusHelpDesk · Admin Portal · Port 5175</div>
    </section>
  </main>;
}
