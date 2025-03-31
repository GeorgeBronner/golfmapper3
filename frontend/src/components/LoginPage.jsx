import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../config';
import { generateUserMap } from '../utils/mapUtils';

function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const handleSubmit = (event) => {
        event.preventDefault();
        axios.post(`${API_BASE_URL}/auth/token`, {
            username: username,
            password: password,
        }, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
            .then(response => {
                localStorage.setItem('token', response.data.access_token);
                generateUserMap();
                navigate('/course_list');
            })
            .catch(error => {
                console.error(error);
            });
        setUsername('');
        setPassword('');
    };

    return (
        <form onSubmit={handleSubmit}>
            <label>
                Username:
                <input type="text" value={username} onChange={e => setUsername(e.target.value)} />
            </label>
            <label>
                Password:
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
            </label>
            <input type="submit" value="Login" />
        </form>
    );
}

export default LoginPage;