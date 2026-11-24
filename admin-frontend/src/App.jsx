import { useEffect, useState } from 'react';
import AdminLogin from './components/AdminLogin';
import AdminDashboard from './components/AdminDashboard';
import { adminRequest, ADMIN_TOKEN_KEY, ADMIN_USER_KEY } from './api';

export default function App(){
  const [admin,setAdmin]=useState(null); const [checking,setChecking]=useState(true);
  useEffect(()=>{ let active=true; async function verify(){ const token=sessionStorage.getItem(ADMIN_TOKEN_KEY); if(!token){if(active)setChecking(false);return;} try{const result=await adminRequest('/api/admin/me'); if(active)setAdmin(result.admin);}catch{sessionStorage.removeItem(ADMIN_TOKEN_KEY);sessionStorage.removeItem(ADMIN_USER_KEY);}finally{if(active)setChecking(false);}} verify(); return()=>{active=false;}; },[]);
  if(checking)return <div className="app-loading">Checking administrator session…</div>;
  return admin?<AdminDashboard admin={admin} onLogout={()=>setAdmin(null)}/>:<AdminLogin onLogin={setAdmin}/>;
}
