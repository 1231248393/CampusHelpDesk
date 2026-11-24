export const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000').replace(/\/$/, '');
export const ADMIN_TOKEN_KEY = 'campus_admin_token';
export const ADMIN_USER_KEY = 'campus_admin_user';

export async function adminRequest(path, options = {}) {
  const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
      sessionStorage.removeItem(ADMIN_USER_KEY);
    }
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}
