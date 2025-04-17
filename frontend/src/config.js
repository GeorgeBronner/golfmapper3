const BACKEND_SERVER_IP = process.env.BACKEND_SERVER_IP;
const BACKEND_PORT = process.env.BACKEND_PORT;

export const API_BASE_URL = `https://${BACKEND_SERVER_IP}`;

console.log('VITE_SERVER_IP value:', process.env.VITE_SERVER_IP);
console.log('API_BASE_URL value:', API_BASE_URL);
