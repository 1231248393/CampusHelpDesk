import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, CheckCircle2, Clock3, ClipboardList, LogOut, RefreshCw, Search, ShieldCheck, GraduationCap, Menu, X, ExternalLink, Paperclip, FileText, Download } from 'lucide-react';
import { adminRequest, API_BASE, ADMIN_TOKEN_KEY, ADMIN_USER_KEY } from '../api';

const STATUSES = ['Pending','Under Review','Assigned','In Progress','Resolved','Rejected'];
const statusClass = value => (value || '').toLowerCase().replaceAll(' ','-');

export default function AdminDashboard({ admin, onLogout }) {
  const [complaints,setComplaints]=useState([]); const [loading,setLoading]=useState(true);
  const [error,setError]=useState(''); const [query,setQuery]=useState(''); const [statusFilter,setStatusFilter]=useState('All'); const [priorityFilter,setPriorityFilter]=useState('All'); const [updating,setUpdating]=useState(null);
  const [selected,setSelected]=useState(null); const [mobileOpen,setMobileOpen]=useState(false); const [analytics,setAnalytics]=useState(null); const [analyticsError,setAnalyticsError]=useState(''); const [history,setHistory]=useState([]); const [historyLoading,setHistoryLoading]=useState(false); const [attachments,setAttachments]=useState([]); const [attachmentsLoading,setAttachmentsLoading]=useState(false);

  const load = useCallback(async({quiet=false}={})=>{
    if(!quiet)setLoading(true);
    setError('');
    try {
      const rows=await adminRequest('/api/admin/complaints');
      setComplaints(Array.isArray(rows)?rows:[]);
    } catch(e) {
      setError(`Unable to load complaints: ${e.message}`);
    }
    try {
      const metrics=await adminRequest('/api/admin/analytics');
      setAnalytics(metrics);
      setAnalyticsError('');
    } catch(e) {
      setAnalytics(null);
      setAnalyticsError(e.message || 'Analytics request failed. Check backend/.campus-run/backend.log.');
    } finally {
      if(!quiet)setLoading(false);
    }
  },[]);
  useEffect(()=>{ load(); const timer=window.setInterval(()=>load({quiet:true}),15000); return()=>window.clearInterval(timer); },[load]);

  const stats=useMemo(()=>({ total:complaints.length, pending:complaints.filter(c=>c.status==='Pending').length, active:complaints.filter(c=>['Under Review','Assigned','In Progress'].includes(c.status)).length, resolved:complaints.filter(c=>c.status==='Resolved').length }),[complaints]);
  const filtered=useMemo(()=>complaints.filter(c=>{const matchesQuery=`${c.complaint_id} ${c.title} ${c.category} ${c.location} ${c.status} ${c.priority} ${c.student_name || ''} ${c.student_roll_number || ''} ${c.student_email || ''}`.toLowerCase().includes(query.toLowerCase());const matchesStatus=statusFilter==='All'||c.status===statusFilter;const matchesPriority=priorityFilter==='All'||c.priority===priorityFilter;return matchesQuery&&matchesStatus&&matchesPriority;}),[complaints,query,statusFilter,priorityFilter]);

  async function changeStatus(id,status){ setUpdating(id); setError(''); try { await adminRequest(`/api/admin/complaints/${id}/status`,{method:'PATCH',body:JSON.stringify({status})}); setComplaints(old=>old.map(c=>c.complaint_id===id?{...c,status}:c)); if(selected?.complaint_id===id)setSelected(old=>({...old,status})); if(selected?.complaint_id===id)loadHistory(id); } catch(e){setError(e.message);} finally{setUpdating(null);} }
  async function changePriority(id,priority){ setUpdating(id); setError(''); try { await adminRequest(`/api/admin/complaints/${id}/priority`,{method:'PATCH',body:JSON.stringify({priority})}); setComplaints(old=>old.map(c=>c.complaint_id===id?{...c,priority}:c)); if(selected?.complaint_id===id)setSelected(old=>({...old,priority})); if(selected?.complaint_id===id)loadHistory(id); } catch(e){setError(e.message);} finally{setUpdating(null);} }
  const loadHistory = useCallback(async(id)=>{ setHistoryLoading(true); try { const rows=await adminRequest(`/api/admin/complaints/${id}/history`); setHistory(Array.isArray(rows)?rows:[]); } catch(e){ setHistory([]); setError(`Unable to load complaint history: ${e.message}`); } finally { setHistoryLoading(false); } },[]);
  const loadAttachments = useCallback(async(id)=>{ setAttachmentsLoading(true); try { const rows=await adminRequest(`/api/admin/complaints/${id}/attachments`); setAttachments(Array.isArray(rows)?rows:[]); } catch(e) { setAttachments([]); if(!String(e.message).includes('404')) setError(`Unable to load attachments: ${e.message}`); } finally { setAttachmentsLoading(false); } },[]);
  useEffect(()=>{ if(selected?.complaint_id) { loadHistory(selected.complaint_id); loadAttachments(selected.complaint_id); } else { setHistory([]); setAttachments([]); } },[selected?.complaint_id,loadHistory,loadAttachments]);
  async function downloadAttachment(item){ try { const token=sessionStorage.getItem(ADMIN_TOKEN_KEY); const response=await fetch(`${API_BASE}/api/admin/attachments/${item.attachment_id}/download`,{headers:{Authorization:`Bearer ${token}`}}); if(!response.ok) { const data=await response.json().catch(()=>({})); throw new Error(data.error||'Download failed'); } const blob=await response.blob(); const url=URL.createObjectURL(blob); const link=document.createElement('a'); link.href=url; link.download=item.original_name; link.click(); URL.revokeObjectURL(url); } catch(e) { setError(e.message); } }

  function exportComplaints(){ const columns=['complaint_id','title','category','location','student_name','student_roll_number','priority','status','created_at']; const quote=v=>`"${String(v??'').replaceAll('\"','\"\"')}"`; const csv=[columns.join(','),...filtered.map(row=>columns.map(key=>quote(row[key])).join(','))].join('\n'); const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})); const link=document.createElement('a'); link.href=url; link.download='campus-helpdesk-complaints.csv'; link.click(); URL.revokeObjectURL(url); }
  async function logout(){ try { await adminRequest('/api/admin/logout',{method:'POST',body:'{}'}); } catch(e) { /* Clear local session even if server is unavailable. */ } finally { sessionStorage.removeItem(ADMIN_TOKEN_KEY); sessionStorage.removeItem(ADMIN_USER_KEY); onLogout(); } }

  return <div className="admin-app">
    <aside className={`admin-sidebar ${mobileOpen?'open':''}`}>
      <div className="admin-brand"><span className="admin-brand-icon"><GraduationCap size={22}/></span><span><b>CampusHelp</b><small>ADMINISTRATION</small></span><button className="mobile-close" onClick={()=>setMobileOpen(false)}><X/></button></div>
      <div className="side-label">WORKSPACE</div><div className="side-link active"><Activity size={18}/> Overview</div><a className="side-link" href="#complaints" onClick={()=>setMobileOpen(false)}><ClipboardList size={18}/> Complaints</a>
      <div className="sidebar-bottom"><div className="admin-security"><ShieldCheck size={18}/><div><b>Secure session</b><small>Administrator access</small></div></div><button className="logout-btn" onClick={logout}><LogOut size={17}/> Sign out</button><small className="version">CampusHelpDesk v1.0</small></div>
    </aside>
    {mobileOpen&&<button className="mobile-scrim" aria-label="Close navigation" onClick={()=>setMobileOpen(false)}/>}
    <main className="admin-main">
      <header className="admin-topbar"><button className="mobile-menu" onClick={()=>setMobileOpen(true)}><Menu/></button><div><h1>Administrator Dashboard</h1><p>Monitor and manage student complaints</p></div><div className="admin-user"><span className="admin-avatar">{(admin?.username||'A').slice(0,1).toUpperCase()}</span><span><b>{admin?.username||'Administrator'}</b><small>Administrator</small></span></div></header>
      <section className="admin-welcome"><div><span className="welcome-tag">CAMPUS HELP CENTER · ADMIN</span><h2>Welcome, {admin?.username||'Administrator'}</h2><p>Review incoming issues and keep campus support moving.</p></div><div className="welcome-shield"><ShieldCheck size={54}/></div></section>
      <div className="section-head"><div><h2>Complaint overview</h2><p>Live totals from the shared CampusHelpDesk database</p></div><button className="refresh-button" onClick={()=>load()} disabled={loading}><RefreshCw size={16} className={loading?'spin':''}/> Refresh</button></div>
      <section className="admin-stats">
        <Stat icon={<ClipboardList/>} label="Total complaints" value={stats.total} tone="blue"/>
        <Stat icon={<Clock3/>} label="Pending" value={stats.pending} tone="amber"/>
        <Stat icon={<AlertCircle/>} label="In progress" value={stats.active} tone="violet"/>
        <Stat icon={<CheckCircle2/>} label="Resolved" value={stats.resolved} tone="green"/>
      </section>
      <section className="admin-panel phase6-analytics" aria-label="AI and complaint analytics">
        <div className="panel-title"><div><h2>Phase 6 · Complaint intelligence</h2><p>Live database analytics and operational trends</p></div><span className="analytics-tag">RULE-BASED TRIAGE · HUMAN REVIEW</span></div>
        {analyticsError && <div className="alert-error wide" role="alert"><AlertCircle size={18}/>Analytics API failed: {analyticsError}. Check the backend log for the SQL error.</div>}
        {analytics ? <div className="analytics-grid">
          <div className="analytics-card"><h3>Priority distribution</h3>{(analytics.priorities||[]).map(x=><BarRow key={x.label} label={x.label} count={x.count} total={analytics.totals?.total||0}/>)}</div>
          <div className="analytics-card"><h3>Complaint categories</h3>{(analytics.categories||[]).length ? analytics.categories.map(x=><BarRow key={x.label} label={x.label} count={x.count} total={analytics.totals?.total||0}/>) : <p>No category data yet.</p>}</div>
          <div className="analytics-card"><h3>Status distribution</h3>{(analytics.statuses||[]).map(x=><BarRow key={x.label} label={x.label} count={x.count} total={analytics.totals?.total||0}/>)}</div>
          <div className="analytics-card"><h3>Last six months</h3>{(analytics.monthly||[]).length ? analytics.monthly.map(x=><BarRow key={x.month} label={x.month} count={x.count} total={Math.max(...analytics.monthly.map(m=>m.count),1)}/>) : <p>No monthly data yet.</p>}</div>
        </div> : <div className="table-empty">{analyticsError ? 'Analytics could not be loaded. Your complaints remain available above.' : 'No analytics data is currently available.'}</div>}
        <p className="analytics-note">AI category, urgency and department suggestions are advisory only. Administrators must verify safety risks and make final assignment decisions.</p>
      </section>
      <section className="admin-panel" id="complaints">
        <div className="panel-title"><div><h2>All student complaints</h2><p>Review details and update complaint status and priority.</p></div><div className="admin-tools"><button className="refresh-button" onClick={exportComplaints} disabled={!filtered.length}>Export CSV</button><label className="admin-filter"><span>Status</span><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>{["All",...STATUSES].map(s=><option key={s}>{s}</option>)}</select></label><label className="admin-filter"><span>Priority</span><select value={priorityFilter} onChange={e=>setPriorityFilter(e.target.value)}>{["All","High","Medium","Low"].map(s=><option key={s}>{s}</option>)}</select></label><div className="admin-search"><Search size={17}/><input placeholder="Search complaints…" value={query} onChange={e=>setQuery(e.target.value)}/></div></div></div>
        {error&&<div className="alert-error wide" role="alert"><AlertCircle size={18}/>{error}</div>}
        {loading?<div className="table-empty">Loading complaints…</div>:filtered.length===0?<div className="table-empty"><ClipboardList size={34}/><b>No complaints found</b><span>{query||statusFilter!=='All'||priorityFilter!=='All'?'Try changing your search or filters.':'No student complaints have been submitted yet.'}</span></div>:
        <div className="table-scroll"><table className="admin-table"><thead><tr><th>ID</th><th>COMPLAINT</th><th>CATEGORY / LOCATION</th><th>SUBMITTED BY</th><th>PRIORITY</th><th>STATUS</th><th>DETAILS</th></tr></thead><tbody>{filtered.map(c=><tr key={c.complaint_id}><td>#{c.complaint_id}</td><td><b>{c.title}</b><small>{c.created_at?new Date(c.created_at).toLocaleString():''}</small></td><td>{c.category}<small>{c.location}</small></td><td>{c.student_name || 'Legacy / unassigned'}<small>{c.student_roll_number || 'No student account linked'}</small></td><td><select className={`status-select ${statusClass(c.priority)}`} value={c.priority||'Medium'} disabled={updating===c.complaint_id} onChange={e=>changePriority(c.complaint_id,e.target.value)} aria-label={`Change priority for complaint ${c.complaint_id}`}><option>Low</option><option>Medium</option><option>High</option></select></td><td><select className={`status-select ${statusClass(c.status)}`} value={c.status} disabled={updating===c.complaint_id} onChange={e=>changeStatus(c.complaint_id,e.target.value)} aria-label={`Change status for complaint ${c.complaint_id}`}>{STATUSES.map(s=><option key={s}>{s}</option>)}</select></td><td><button className="details-button" onClick={()=>setSelected(c)}>View <ExternalLink size={14}/></button></td></tr>)}</tbody></table></div>}
        <div className="table-footer">Showing {filtered.length} of {complaints.length} complaints</div>
      </section>
      <footer className="admin-footer">© {new Date().getFullYear()} CampusHelpDesk · College Complaint Management System</footer>
    </main>
    {selected&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}><section className="complaint-modal"><div className="modal-head"><div><span className="welcome-tag">COMPLAINT #{selected.complaint_id}</span><h2>{selected.title}</h2></div><button className="modal-close" onClick={()=>setSelected(null)}><X/></button></div><div className="detail-grid"><Detail label="Category" value={selected.category}/><Detail label="Location" value={selected.location}/><Detail label="Priority" value={selected.priority}/><Detail label="Status" value={selected.status}/><Detail label="Submitted" value={selected.created_at?new Date(selected.created_at).toLocaleString():'—'}/><Detail label="Student" value={selected.student_name || 'Legacy / unassigned'}/><Detail label="Roll number" value={selected.student_roll_number || '—'}/><Detail label="Student email" value={selected.student_email || '—'}/><Detail label="AI suggested department" value={selected.ai_suggested_department || 'Not available'}/></div><h3>Description</h3><p className="description-text">{selected.description||'No description supplied.'}</p><h3 className="history-heading"><Paperclip size={16}/> Student attachments</h3>{attachmentsLoading?<p className="description-text">Loading attachments…</p>:attachments.length===0?<p className="description-text">No evidence files attached to this complaint.</p>:<div className="admin-attachment-list">{attachments.map(item=><button type="button" key={item.attachment_id} onClick={()=>downloadAttachment(item)}><FileText size={16}/><span>{item.original_name}<small>{Math.ceil(item.file_size/1024)} KB</small></span><Download size={15}/></button>)}</div>}<label className="modal-label">Update priority</label><select className={`status-select ${statusClass(selected.priority)}`} value={selected.priority||'Medium'} disabled={updating===selected.complaint_id} onChange={e=>changePriority(selected.complaint_id,e.target.value)}><option>Low</option><option>Medium</option><option>High</option></select><label className="modal-label">Update status</label><select className={`status-select ${statusClass(selected.status)}`} value={selected.status} disabled={updating===selected.complaint_id} onChange={e=>changeStatus(selected.complaint_id,e.target.value)}>{STATUSES.map(s=><option key={s}>{s}</option>)}</select><h3 className="history-heading">Complaint activity history</h3>{historyLoading?<p className="description-text">Loading history…</p>:history.length===0?<p className="description-text">No recorded changes yet. New status and priority updates will appear here.</p>:<ol className="complaint-history">{history.map(item=><li key={item.history_id}><b>{item.change_type==='priority'?'Priority':'Status'} changed</b><span>{item.old_value||'—'} → {item.new_value}</span><small>{item.changed_by||'Administrator'} · {item.changed_at?new Date(item.changed_at).toLocaleString():''}</small></li>)}</ol>}</section></div>}
  </div>;
}

function Stat({icon,label,value,tone}){return <article className="admin-stat"><span className={`stat-symbol ${tone}`}>{icon}</span><span className="stat-label">{label}</span><strong>{value}</strong><small>Current records</small></article>}
function Detail({label,value}){return <div className="detail-item"><small>{label}</small><b>{value||'—'}</b></div>}

function BarRow({label,count,total}) { const width = total > 0 ? Math.max(2, Math.round((count/total)*100)) : 0; return <div className="analytics-bar-row"><div><span>{label}</span><b>{count}</b></div><div className="analytics-track"><i style={{width:`${width}%`}}/></div></div>; }
