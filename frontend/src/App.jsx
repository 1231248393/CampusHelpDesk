import { useEffect, useState } from "react";
import StudentAuth from "./StudentAuth";
import {
  LayoutDashboard, ClipboardList, PlusCircle,
  CheckCircle, Clock, AlertCircle, Search,
  RefreshCw, Menu, X, GraduationCap, FileText, Paperclip, Star, Download, History
} from "lucide-react";
import "./App.css";

const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000").replace(/\/$/, "");
const API = `${API_BASE}/api/complaints`;
const STUDENT_TOKEN_KEY = "campus_student_token";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(STUDENT_TOKEN_KEY) || "");
  const [student, setStudent] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [submitting, setSubmitting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [complaintHistory, setComplaintHistory] = useState([]);
  const [complaintAttachments, setComplaintAttachments] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [attachmentFile, setAttachmentFile] = useState(null);

  const [form, setForm] = useState({
    title: "",
    category: "Classroom",
    location: "",
    description: "",
    priority: "Medium"
  });

  async function loadComplaints() {
    if (!token) return;
    try {
      setError("");
      const response = await fetch(API, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 401) {
        localStorage.removeItem(STUDENT_TOKEN_KEY);
        setToken("");
        setStudent(null);
        throw new Error("Your session expired. Please sign in again.");
      }
      if (!response.ok) throw new Error("Unable to load your complaints");
      const data = await response.json();
      setComplaints(data);
      const notificationResponse = await fetch(`${API_BASE}/api/student/notifications`, { headers: { Authorization: `Bearer ${token}` } });
      if (notificationResponse.ok) setNotifications(await notificationResponse.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function verifySession() {
      if (!token) {
        setStudent(null);
        setAuthChecking(false);
        setComplaints([]);
        return;
      }
      setAuthChecking(true);
      try {
        const response = await fetch(`${API_BASE}/api/student/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || "Session expired");
        if (active) setStudent(result.student);
      } catch {
        localStorage.removeItem(STUDENT_TOKEN_KEY);
        if (active) { setToken(""); setStudent(null); }
      } finally {
        if (active) setAuthChecking(false);
      }
    }
    verifySession();
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    loadComplaints();
    const refreshTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") loadComplaints();
    }, 15000);
    const handleFocus = () => loadComplaints();
    window.addEventListener("focus", handleFocus);
    return () => {
      window.clearInterval(refreshTimer);
      window.removeEventListener("focus", handleFocus);
    };
  }, [token]);

  async function analyzeDraft() {
    if (!form.title.trim() || !form.description.trim()) {
      alert("Enter a complaint title and description first.");
      return;
    }
    setAnalyzing(true);
    setAiAnalysis(null);
    try {
      const response = await fetch(`${API_BASE}/api/complaints/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ title: form.title, description: form.description, category: form.category })
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "AI analysis failed");
      const analysis = result.analysis;
      setAiAnalysis(analysis);
      if (["Classroom", "Laboratory", "Library", "Canteen", "Hostel", "Washroom", "IT Support", "Infrastructure", "Other"].includes(analysis.category)) {
        setForm(old => ({ ...old, category: analysis.category, priority: analysis.priority }));
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function submitComplaint(e) {
    e.preventDefault();

    if (submitting) return;
    setSubmitting(true);
    try {
      const response = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form)
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Submission failed");
      }

      alert("Complaint submitted! ID: " + result.complaint_id);

      setForm({
        title: "",
        category: "Classroom",
        location: "",
        description: "",
        priority: "Medium"
      });

      setShowForm(false);
      if (attachmentFile) {
        const uploadData = new FormData();
        uploadData.append("file", attachmentFile);
        try {
          const uploadResponse = await fetch(`${API_BASE}/api/student/complaints/${result.complaint_id}/attachments`, {
            method: "POST", headers: { Authorization: `Bearer ${token}` }, body: uploadData
          });
          const uploadResult = await uploadResponse.json().catch(() => ({}));
          if (!uploadResponse.ok) {
            alert(`Complaint was saved, but the attachment was not uploaded: ${uploadResult.error || "Upload failed"}`);
          }
        } catch {
          alert("Complaint was saved, but the attachment upload could not connect. You can open the complaint and try again later.");
        }
      }
      setAttachmentFile(null);
      await loadComplaints();

    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function openComplaintDetails(complaint) {
    setSelectedComplaint(complaint);
    setDetailLoading(true);
    setComplaintHistory([]);
    setComplaintAttachments([]);
    setFeedback(null);
    setFeedbackRating(5);
    setFeedbackComment("");
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [historyResponse, attachmentResponse, feedbackResponse] = await Promise.all([
        fetch(`${API_BASE}/api/student/complaints/${complaint.complaint_id}/history`, { headers }),
        fetch(`${API_BASE}/api/student/complaints/${complaint.complaint_id}/attachments`, { headers }),
        fetch(`${API_BASE}/api/student/complaints/${complaint.complaint_id}/feedback`, { headers })
      ]);
      if (historyResponse.ok) setComplaintHistory(await historyResponse.json());
      if (attachmentResponse.ok) setComplaintAttachments(await attachmentResponse.json());
      if (feedbackResponse.ok) {
        const saved = await feedbackResponse.json();
        if (saved && saved.rating) {
          setFeedback(saved);
          setFeedbackRating(saved.rating);
          setFeedbackComment(saved.comment || "");
        }
      }
    } catch (err) {
      console.error("Unable to load complaint details", err);
    } finally {
      setDetailLoading(false);
    }
  }

  async function saveComplaintFeedback() {
    if (!selectedComplaint || savingFeedback) return;
    setSavingFeedback(true);
    try {
      const response = await fetch(`${API_BASE}/api/student/complaints/${selectedComplaint.complaint_id}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ rating: feedbackRating, comment: feedbackComment })
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to save feedback");
      setFeedback({ rating: feedbackRating, comment: feedbackComment });
      alert("Thank you for your feedback!");
    } catch (err) {
      alert(err.message);
    } finally {
      setSavingFeedback(false);
    }
  }

  async function downloadComplaintAttachment(item) {
    try {
      const response = await fetch(`${API_BASE}/api/student/attachments/${item.attachment_id}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Unable to download attachment");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.original_name;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  }

  function handleAuth(result) {
    localStorage.setItem(STUDENT_TOKEN_KEY, result.access_token);
    setStudent(result.student);
    setToken(result.access_token);
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/api/student/logout`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }
      });
    } finally {
      localStorage.removeItem(STUDENT_TOKEN_KEY);
      setToken("");
      setStudent(null);
      setComplaints([]);
    }
  }

  if (authChecking) return <div className="student-auth-loading">Checking your secure session…</div>;
  if (!token || !student) return <StudentAuth onAuth={handleAuth} />;

  const pending = complaints.filter(
    c => c.status === "Pending"
  ).length;

  const progress = complaints.filter(
    c => c.status === "In Progress" ||
         c.status === "Assigned" ||
         c.status === "Under Review"
  ).length;

  const resolved = complaints.filter(
    c => c.status === "Resolved"
  ).length;

  const filtered = complaints.filter(c => {
    const matchesSearch = `${c.title} ${c.category} ${c.location} ${c.complaint_id}`
      .toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "All" || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="app">

      <aside className={`sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon"><GraduationCap/></div>
          <div>
            <h2>CampusHelp</h2>
            <small>STUDENT PORTAL</small>
          </div>
          <button className="close-menu" onClick={() => setMobileMenu(false)}>
            <X/>
          </button>
        </div>

        <p className="nav-heading">MAIN MENU</p>

        <div className="nav-item active">
          <LayoutDashboard size={19}/> Dashboard
        </div>

        <div className="nav-item" onClick={() => setShowForm(true)}>
          <PlusCircle size={19}/> Submit Complaint
        </div>

        <div className="nav-item" onClick={() =>
          document.getElementById("complaints")?.scrollIntoView({behavior:"smooth"})
        }>
          <ClipboardList size={19}/> My Complaints
        </div>

        <div className="sidebar-bottom">
          <div className="support-box">
            <strong>Need assistance?</strong>
            <p>Report your campus problems here.</p>
          </div>
          <small>CampusHelpDesk v1.0</small>
        </div>
      </aside>
      {mobileMenu && <button className="student-scrim" aria-label="Close navigation" onClick={() => setMobileMenu(false)} />}

      <main className="main">

        <header className="topbar">
          <button className="menu-toggle" onClick={() => setMobileMenu(!mobileMenu)}>
            <Menu/>
          </button>
          <div>
            <h3>Student Dashboard</h3>
            <p>College Complaint Management System</p>
          </div>
          <div className="user-profile">
            <div className="avatar">{(student.full_name || "S").charAt(0).toUpperCase()}</div>
            <div><strong>{student.full_name}</strong><small>{student.roll_number}</small></div>
            <button className="student-logout" onClick={logout}>Sign out</button>
          </div>
        </header>

        <section className="welcome">
          <div>
            <span className="welcome-label">CAMPUS HELP CENTER</span>
            <h1>Welcome to CampusHelpDesk!</h1>
            <p>Report problems. Track progress. Improve your campus.</p>
            <button className="welcome-btn" onClick={() => setShowForm(true)}>
              <PlusCircle size={17}/> Submit a Complaint
            </button>
          </div>
          <div className="welcome-icon"><GraduationCap size={85}/></div>
        </section>

        {notifications.length > 0 && <section className="panel" aria-label="Notifications" style={{marginBottom: "18px"}}>
          <div className="panel-header"><div><h2>Notifications</h2><p>Recent updates from campus administration</p></div><strong>{notifications.filter(n => !n.is_read).length} unread</strong></div>
          <div style={{display:"grid",gap:"10px"}}>{notifications.slice(0,5).map(n => <button key={n.notification_id} type="button" onClick={async()=>{await fetch(`${API_BASE}/api/student/notifications/${n.notification_id}/read`,{method:"PATCH",headers:{Authorization:`Bearer ${token}`}});setNotifications(old=>old.map(x=>x.notification_id===n.notification_id?{...x,is_read:true}:x));}} style={{textAlign:"left",padding:"12px",border:"1px solid #dbe5f2",borderRadius:"10px",background:n.is_read?"#fff":"#f0f6ff",cursor:"pointer"}}><b>{n.title}</b><p style={{margin:"4px 0"}}>{n.message}</p><small>{n.created_at ? new Date(n.created_at).toLocaleString() : ""} · {n.is_read ? "Read" : "Click to mark read"}</small></button>)}</div>
        </section>}

        <section className="section-title">
          <div>
            <h2>Complaint Overview</h2>
            <p>Monitor your complaint activity</p>
          </div>
          <button className="refresh-btn" onClick={loadComplaints}>
            <RefreshCw size={16}/> Refresh
          </button>
        </section>

        <section className="stats">
          <div className="stat-card">
            <div className="stat-icon blue"><ClipboardList/></div>
            <p>Total Complaints</p>
            <h2>{complaints.length}</h2>
            <small>All submitted complaints</small>
          </div>

          <div className="stat-card">
            <div className="stat-icon orange"><Clock/></div>
            <p>Pending</p>
            <h2>{pending}</h2>
            <small>Awaiting action</small>
          </div>

          <div className="stat-card">
            <div className="stat-icon purple"><AlertCircle/></div>
            <p>In Progress</p>
            <h2>{progress}</h2>
            <small>Currently being handled</small>
          </div>

          <div className="stat-card">
            <div className="stat-icon green"><CheckCircle/></div>
            <p>Resolved</p>
            <h2>{resolved}</h2>
            <small>Successfully completed</small>
          </div>
        </section>

        {showForm && (
          <section className="panel form-panel">
            <div className="panel-header">
              <div>
                <h2>Submit New Complaint</h2>
                <p>Provide details about your campus problem.</p>
              </div>
              <button className="close-btn" onClick={() => setShowForm(false)}>
                <X/>
              </button>
            </div>

            <form onSubmit={submitComplaint}>
              <div className="form-grid">
                <div>
                  <label>Complaint Title *</label>
                  <input required maxLength="200"
                    placeholder="Example: Projector not working"
                    value={form.title}
                    onChange={e => setForm({...form,title:e.target.value})}/>
                </div>

                <div>
                  <label>Category *</label>
                  <select value={form.category}
                    onChange={e => setForm({...form,category:e.target.value})}>
                    {["Classroom","Laboratory","Library","Canteen",
                      "Hostel","Washroom","IT Support","Infrastructure","Other"].map(x =>
                      <option key={x}>{x}</option>)}
                  </select>
                </div>

                <div>
                  <label>Location *</label>
                  <input required placeholder="Building / Room number"
                    value={form.location}
                    onChange={e => setForm({...form,location:e.target.value})}/>
                </div>

                <div>
                  <label>Priority</label>
                  <select value={form.priority}
                    onChange={e => setForm({...form,priority:e.target.value})}>
                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                  </select>
                </div>
              </div>

              <label>Description *</label>
              <textarea required rows="4"
                placeholder="Explain the problem..."
                value={form.description}
                onChange={e => setForm({...form,description:e.target.value})}/>

              <div className="attachment-field">
                <label htmlFor="complaint-attachment"><Paperclip size={15}/> Attach evidence (optional)</label>
                <input id="complaint-attachment" type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                  onChange={e => setAttachmentFile(e.target.files?.[0] || null)}/>
                <small>PDF, PNG or JPEG · maximum 5 MB. The complaint is saved even if an optional upload fails.</small>
                {attachmentFile && <small className="attachment-selected">Selected: {attachmentFile.name}</small>}
              </div>

              <div className="ai-assist-panel" style={{margin: "12px 0", padding: "14px", border: "1px solid #dbe5f2", borderRadius: "12px", background: "#f7faff"}}>
                <button className="primary-btn" type="button" onClick={analyzeDraft} disabled={analyzing || submitting}>
                  {analyzing ? "Analyzing…" : "Analyze with AI"}
                </button>
                {aiAnalysis && <div role="status" style={{marginTop: "12px", lineHeight: 1.6}}>
                  <strong>AI suggestions (review before submitting)</strong>
                  <p>Category: <b>{aiAnalysis.category}</b> · Priority: <b>{aiAnalysis.priority}</b> · Sentiment: <b>{aiAnalysis.sentiment}</b></p>
                  <p>Suggested department: <b>{aiAnalysis.suggested_department || "Manual review"}</b></p>
                  <p>{aiAnalysis.priority_reason}</p>
                  {aiAnalysis.possible_duplicates?.length > 0 && <p>Possible similar complaints: {aiAnalysis.possible_duplicates.map(x => `#${x.complaint_id} (${Math.round(x.similarity * 100)}%)`).join(", ")}</p>}
                  <small>{aiAnalysis.disclaimer}</small>
                </div>}
              </div>

              <button className="primary-btn" type="submit" disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Complaint"}
              </button>
            </form>
          </section>
        )}

        <section className="panel complaints-panel" id="complaints">
          <div className="panel-header">
            <div>
              <h2>My Complaints</h2>
              <p>View and track your submitted complaints.</p>
            </div>

            <div className="complaint-tools">
              <label className="filter-box" aria-label="Filter complaints by status">
                <span>Status</span>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                  { ["All", "Pending", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"].map(x => <option key={x}>{x}</option>) }
                </select>
              </label>
              <div className="search-box">
                <Search size={17}/>
                <input placeholder="Search complaints..."
                  value={search} onChange={e => setSearch(e.target.value)}/>
              </div>
            </div>
          </div>

          {error && <div className="error-box">{error}. Start the Flask backend and refresh.</div>}

          {loading ? <p>Loading complaints...</p> :
            filtered.length === 0 ?
            <div className="empty-state">
              <ClipboardList size={40}/>
              <h3>No complaints found</h3>
              <p>Submit a complaint to get started.</p>
            </div> :

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Complaint</th>
                    <th>Category</th>
                    <th>Location</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Track</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(c => (
                    <tr key={c.complaint_id}>
                      <td>#{c.complaint_id}</td>
                      <td><strong>{c.title}</strong></td>
                      <td>{c.category}</td>
                      <td>{c.location}</td>
                      <td><span className={`priority ${c.priority.toLowerCase()}`}>{c.priority}</span></td>
                      <td><span className={`status ${c.status.toLowerCase().replaceAll(" ","-")}`}>{c.status}</span></td>
                      <td><button type="button" className="track-button" onClick={() => openComplaintDetails(c)}><History size={14}/> Track</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          }
        </section>

        {selectedComplaint && <div className="student-modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setSelectedComplaint(null); }}>
          <section className="student-detail-modal" role="dialog" aria-modal="true" aria-labelledby="student-complaint-title">
            <div className="student-modal-head">
              <div><span className="welcome-label">COMPLAINT #{selectedComplaint.complaint_id}</span><h2 id="student-complaint-title">{selectedComplaint.title}</h2><p>{selectedComplaint.category} · {selectedComplaint.location}</p></div>
              <button className="close-btn" onClick={() => setSelectedComplaint(null)} aria-label="Close details"><X/></button>
            </div>
            <div className="student-detail-grid">
              <div><small>Current status</small><b>{selectedComplaint.status}</b></div>
              <div><small>Priority</small><b>{selectedComplaint.priority}</b></div>
              <div><small>Submitted</small><b>{selectedComplaint.created_at ? new Date(selectedComplaint.created_at).toLocaleString() : "—"}</b></div>
            </div>
            <h3><History size={17}/> Progress timeline</h3>
            {detailLoading ? <p className="detail-muted">Loading complaint history…</p> : complaintHistory.length === 0 ? <p className="detail-muted">No status changes have been recorded yet. Your complaint is still being tracked.</p> : <ol className="student-timeline">{complaintHistory.map(item => <li key={item.history_id}><b>{item.change_type === "priority" ? "Priority updated" : "Status updated"}</b><span>{item.old_value || "Submitted"} → {item.new_value}</span><small>{item.changed_by || "Campus administration"} · {item.changed_at ? new Date(item.changed_at).toLocaleString() : ""}</small></li>)}</ol>}
            <h3><Paperclip size={17}/> Attachments</h3>
            {complaintAttachments.length === 0 ? <p className="detail-muted">No attachments uploaded for this complaint.</p> : <div className="student-attachment-list">{complaintAttachments.map(item => <button key={item.attachment_id} type="button" onClick={() => downloadComplaintAttachment(item)}><FileText size={16}/><span>{item.original_name}<small>{Math.ceil(item.file_size / 1024)} KB</small></span><Download size={15}/></button>)}</div>}
            {selectedComplaint.status === "Resolved" && <div className="student-feedback-box"><h3><Star size={17}/> Rate the resolution</h3><p>Share your experience to help improve campus support.</p><div className="rating-picker" role="group" aria-label="Resolution rating">{[1,2,3,4,5].map(value => <button key={value} type="button" className={value <= feedbackRating ? "selected" : ""} onClick={() => setFeedbackRating(value)} aria-label={`${value} star${value>1?"s":""}`}><Star size={22} fill={value <= feedbackRating ? "currentColor" : "none"}/></button>)}</div><textarea rows="3" maxLength="1000" placeholder="Optional comments about the resolution…" value={feedbackComment} onChange={e => setFeedbackComment(e.target.value)}/><button type="button" className="primary-btn" onClick={saveComplaintFeedback} disabled={savingFeedback}>{savingFeedback ? "Saving…" : feedback ? "Update feedback" : "Submit feedback"}</button>{feedback && <small className="feedback-saved">Your feedback has been saved.</small>}</div>}
          </section>
        </div>}

        <footer>© 2026 CampusHelpDesk · College Student Support System</footer>
      </main>
    </div>
  );
}
