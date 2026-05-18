import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

function NewUser() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        try {
            await api.post('/auth/', { username, password });
            navigate('/');
        } catch {
            setError('Registration failed. That username may already be taken.');
        }
        setUsername('');
        setPassword('');
    };

    return (
        <div className="login-shell">
            <div className="login-hero">
                <div className="login-hero-logo">⛳ GolfMapper</div>
                <div>
                    <div className="login-hero-tagline">
                        Join the <span>golfer's</span><br />journal.
                    </div>
                    <div className="login-hero-sub">
                        Track every course you've played, mapped beautifully.
                    </div>
                </div>
                <div className="login-hero-dots">
                    <div className="login-hero-dot" />
                    <div className="login-hero-dot active" />
                    <div className="login-hero-dot" />
                </div>
            </div>

            <div className="login-form-panel">
                <div>
                    <div className="login-form-title">Create an account</div>
                    <div className="login-form-subtitle">Free forever. No credit card needed.</div>
                </div>

                {error && <div className="alert-danger">{error}</div>}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-username">Username</label>
                        <input
                            id="reg-username"
                            className="form-input"
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="choose_a_username"
                            autoComplete="username"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-password">Password</label>
                        <input
                            id="reg-password"
                            className="form-input"
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            autoComplete="new-password"
                        />
                    </div>
                    <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '11px' }}>
                        Create Account
                    </button>
                </form>

                <div className="login-footer-link">
                    Already have an account? <a href="/">Sign in →</a>
                </div>
            </div>
        </div>
    );
}

export default NewUser;
