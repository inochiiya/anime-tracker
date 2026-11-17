const API_BASE = '/api';

let _adminToken = localStorage.getItem('admin_token') || '';

function setAdminToken(token) {
    _adminToken = token || '';
    if (_adminToken) {
        localStorage.setItem('admin_token', _adminToken);
    } else {
        localStorage.removeItem('admin_token');
    }
}

function getAdminToken() {
    return _adminToken;
}

function _headers(extra) {
    const h = { ...(extra || {}) };
    if (_adminToken) {
        h['X-Admin-Token'] = _adminToken;
    }
    return h;
}

async function apiGet(path, params = {}) {
    const url = new URL(API_BASE + path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') {
            url.searchParams.set(k, v);
        }
    });
    const res = await fetch(url, { headers: _headers() });
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
}

async function apiPost(path, data) {
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: _headers({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API Error: ${res.status}`);
    }
    return res.json();
}

async function apiPut(path, data) {
    const res = await fetch(API_BASE + path, {
        method: 'PUT',
        headers: _headers({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API Error: ${res.status}`);
    }
    return res.json();
}

async function apiDelete(path) {
    const res = await fetch(API_BASE + path, {
        method: 'DELETE',
        headers: _headers(),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API Error: ${res.status}`);
    }
    return res.json();
}
