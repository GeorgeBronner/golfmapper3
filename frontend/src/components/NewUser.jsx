import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';

function NewUser() {
    const [form, setForm] = useState({ username: '', email: '', first_name: '', last_name: '', password: '' });
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleChange = e => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const isValidEmail = email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        if (!isValidEmail(form.email)) {
            setError('Please enter a valid email address.');
            return;
        }
        try {
            await api.post('/auth/', form);
            navigate('/');
        } catch {
            setError('Registration failed. That username or email may already be taken.');
        }
        setForm({ username: '', email: '', first_name: '', last_name: '', password: '' });
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

                {error && <div className="alert-danger" role="alert">{error}</div>}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <div className="form-group" style={{ flex: 1 }}>
                            <label className="form-label" htmlFor="reg-first-name">First Name</label>
                            <input
                                id="reg-first-name"
                                className="form-input"
                                type="text"
                                name="first_name"
                                value={form.first_name}
                                onChange={handleChange}
                                placeholder="Jane"
                                autoComplete="given-name"
                                required
                            />
                        </div>
                        <div className="form-group" style={{ flex: 1 }}>
                            <label className="form-label" htmlFor="reg-last-name">Last Name</label>
                            <input
                                id="reg-last-name"
                                className="form-input"
                                type="text"
                                name="last_name"
                                value={form.last_name}
                                onChange={handleChange}
                                placeholder="Doe"
                                autoComplete="family-name"
                                required
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-email">Email</label>
                        <input
                            id="reg-email"
                            className="form-input"
                            type="email"
                            name="email"
                            value={form.email}
                            onChange={handleChange}
                            placeholder="jane@example.com"
                            autoComplete="email"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-username">Username</label>
                        <input
                            id="reg-username"
                            className="form-input"
                            type="text"
                            name="username"
                            value={form.username}
                            onChange={handleChange}
                            placeholder="choose_a_username"
                            autoComplete="username"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="reg-password">Password</label>
                        <input
                            id="reg-password"
                            className="form-input"
                            type="password"
                            name="password"
                            value={form.password}
                            onChange={handleChange}
                            placeholder="••••••••"
                            autoComplete="new-password"
                            required
                        />
                    </div>
                    <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '11px' }}>
                        Create Account
                    </button>
                </form>

                <div className="login-footer-link">
                    Already have an account? <Link to="/">Sign in →</Link>
                </div>
            </div>
        </div>
    );
}

export default NewUser;
