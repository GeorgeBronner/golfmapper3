const BACKEND_SERVER_IP = import.meta.env.VITE_BACKEND_SERVER_IP;
const BACKEND_PROTOCOL = import.meta.env.VITE_BACKEND_PROTOCOL || 'http';
const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '80';

export const API_BASE_URL = `${BACKEND_PROTOCOL}://${BACKEND_SERVER_IP}:${BACKEND_PORT}`;

console.log('import.meta.env.VITE_BACKEND_SERVER_IP value:', import.meta.env.VITE_BACKEND_SERVER_IP);
console.log('import.meta.env.VITE_BACKEND_PORT value:', import.meta.env.VITE_BACKEND_PORT);
console.log('API_BASE_URL value:', API_BASE_URL);
