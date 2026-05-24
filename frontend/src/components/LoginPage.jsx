import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
        <div className="login-shell">
            {/* Left hero panel */}
            <div className="login-hero">
                <div className="login-hero-logo">⛳ GolfMapper</div>
                <div>
                    <div className="login-hero-tagline">
                        Track every course<br />you've <span>ever played.</span>
                    </div>
                    <div className="login-hero-sub">
                        Your personal golf course journal, beautifully mapped.
                    </div>
                </div>
                <div className="login-hero-dots">
                    <div className="login-hero-dot active" />
                    <div className="login-hero-dot" />
                    <div className="login-hero-dot" />
                </div>
            </div>

            {/* Right form panel */}
            <div className="login-form-panel">
                <div>
                    <div className="login-form-title">Welcome back</div>
                    <div className="login-form-subtitle">Sign in to your GolfMapper account</div>
                </div>

                {error && <div className="alert-danger" role="alert">{error}</div>}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="login-username">Username</label>
                        <input
                            id="login-username"
                            className="form-input"
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="your_username"
                            autoComplete="username"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="login-password">Password</label>
                        <input
                            id="login-password"
                            className="form-input"
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            autoComplete="current-password"
                        />
                    </div>
                    <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '11px' }}>
                        Sign In
                    </button>
                </form>

                <div className="login-footer-link" style={{ textAlign: 'center' }}>
                    <Link to="/forgot-password">Forgot password?</Link>
                </div>
                <div className="login-footer-link">
                    Don't have an account? <Link to="/register">Create one free →</Link>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
