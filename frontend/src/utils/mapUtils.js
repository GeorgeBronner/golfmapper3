import axios from 'axios';
import { API_BASE_URL } from '../config';

export const generateUserMap = () => {
    return axios.get(`${API_BASE_URL}/map/user_map_generate`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })
        .then(response => {
            console.log(response);
        })
        .catch(error => {
            console.error(error);
        });
}; 