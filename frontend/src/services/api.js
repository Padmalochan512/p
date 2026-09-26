const API_BASE_URL = '/api';

export function getAuthToken() {
  return localStorage.getItem('token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...options.headers
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401 && !endpoint.includes('/auth/login')) {
    // Session expired or unauthenticated
    setAuthToken('');
    window.location.href = '/';
  }

  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = await response.text() || errorDetail;
    }
    throw new Error(errorDetail);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return await response.json();
  }
  return response;
}

export const api = {
  // Auth
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  }),
  register: (payload) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getMe: () => request('/auth/me'),

  // Dashboard
  getDashboardSummary: () => request('/dashboard/summary'),
  getDashboardActivity: () => request('/dashboard/activity'),

  // Documents
  uploadDocuments: (files) => {
    const formData = new FormData();
    for (let f of files) {
      formData.append('files', f);
    }
    return request('/documents/upload', {
      method: 'POST',
      body: formData
    });
  },
  getDocuments: () => request('/documents'),
  getDocument: (id) => request(`/documents/${id}`),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),

  // Invoices
  getInvoices: (params = {}) => {
    const qs = new URLSearchParams();
    Object.keys(params).forEach(k => {
      if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
        qs.append(k, params[k]);
      }
    });
    return request(`/invoices?${qs.toString()}`);
  },
  getInvoice: (id) => request(`/invoices/${id}`),
  updateInvoice: (id, payload) => request(`/invoices/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  approveInvoice: (id) => request(`/invoices/${id}/approve`, { method: 'POST' }),
  markForReview: (id) => request(`/invoices/${id}/review`, { method: 'POST' }),
  reprocessInvoice: (id) => request(`/invoices/${id}/reprocess`, { method: 'POST' }),
  deleteInvoice: (id) => request(`/invoices/${id}`, { method: 'DELETE' }),
  generateSamples: () => request('/invoices/generate-samples', { method: 'POST' }),

  // Reports
  getReportsSummary: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.start_date) qs.append('start_date', params.start_date);
    if (params.end_date) qs.append('end_date', params.end_date);
    return request(`/reports/summary?${qs.toString()}`);
  },

  // Notifications
  getNotifications: () => request('/notifications'),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: 'PUT' }),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'PUT' }),

  // Settings
  getSettings: () => request('/settings'),
  updateSettings: (payload) => request('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
};
