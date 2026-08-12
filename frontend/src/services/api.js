import axios from 'axios';
import { API_BASE_URL } from '../config';
import { SESSION_EXPIRED_EVENT } from '../constants/authEvents';

const api = axios.create({ baseURL: `${API_BASE_URL}/api/v1` });

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// Endpoints where a 401 is an expected outcome (bad credentials / invalid
// reset token) and must be handled by the calling component, not trigger a
// global logout-and-redirect.
const AUTH_ENDPOINTS = ['/auth/token', '/auth/forgot-password', '/auth/reset-password'];

api.interceptors.response.use(
    res => res,
    err => {
        const url = err.config?.url || '';
        const isAuthEndpoint = AUTH_ENDPOINTS.some(path => url.includes(path));
        if (err.response?.status === 401 && !isAuthEndpoint) {
            localStorage.removeItem('token');
            // Let AuthProvider clear its state and the router navigate away
            // in-app instead of a hard reload, which would silently wipe
            // any unsaved form data on the current page.
            window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
        }
        return Promise.reject(err);
    }
);

export default api;
