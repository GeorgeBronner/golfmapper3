console.log('VITE_SERVER_IP value:', process.env.VITE_SERVER_IP);

const BACKEND_SERVER_IP = process.env.BACKEND_SERVER_IP || '127.0.0.1';

export const API_BASE_URL = `http://${BACKEND_SERVER_IP}:8005`;