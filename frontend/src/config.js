const BACKEND_SERVER_IP = import.meta.env.VITE_BACKEND_SERVER_IP;
const BACKEND_PROTOCOL = import.meta.env.VITE_BACKEND_PROTOCOL || 'http';
const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '80';

// The backend serves the built frontend in production, so when no backend
// host is configured at build time, same-origin is the right default.
export const API_BASE_URL = BACKEND_SERVER_IP
    ? `${BACKEND_PROTOCOL}://${BACKEND_SERVER_IP}:${BACKEND_PORT}`
    : window.location.origin;
