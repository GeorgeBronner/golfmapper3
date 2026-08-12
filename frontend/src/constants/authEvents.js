// Dispatched by services/api.js on a non-whitelisted 401; handled by
// AuthProvider.jsx (clears auth state) and App.jsx (navigates + flash message).
export const SESSION_EXPIRED_EVENT = 'auth:session-expired';
