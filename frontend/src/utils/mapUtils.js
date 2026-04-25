import api from '../services/api';

export const generateUserMap = () => {
    return api.get('/map/user_map_generate')
        .then(response => response.data)
        .catch(error => {
            console.error(error);
        });
};
