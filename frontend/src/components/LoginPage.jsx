import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import api from '../services/api';

function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const { setToken } = useAuth();

    const handleSubmit = (event) => {
        event.preventDefault();
        setError('');
        api.post('/auth/token', new URLSearchParams({ username, password }), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })
            .then(response => {
                setToken(response.data.access_token);
                setUsername('');
                setPassword('');
                navigate('/course_list');
            })
            .catch(() => {
                setError('Invalid username or password.');
            });
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-danger" role="alert">{error}</div>}
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
