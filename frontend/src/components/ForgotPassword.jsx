import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';

function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        api.post('/auth/forgot-password', { email })
            .then(() => setSubmitted(true))
            .catch(() => setError('Something went wrong. Please try again.'))
            .finally(() => setLoading(false));
    };

    return (
        <div className="login-shell">
            <div className="login-hero">
                <div className="login-hero-logo">⛳ GolfMapper</div>
                <div>
                    <div className="login-hero-tagline">
                        Forgot your<br />password?
                    </div>
                    <div className="login-hero-sub">
                        No worries — we'll send you a reset link.
                    </div>
                </div>
            </div>

            <div className="login-form-panel">
                <div>
                    <div className="login-form-title">Reset password</div>
                    <div className="login-form-subtitle">Enter your account email address</div>
                </div>

                {submitted ? (
                    <div>
                        <div className="alert-success" role="alert">
                            If that email is registered, a reset link has been sent. Check your inbox.
                        </div>
                        <div className="login-footer-link" style={{ marginTop: '1rem' }}>
                            <Link to="/">← Back to sign in</Link>
                        </div>
                    </div>
                ) : (
                    <>
                        {error && <div className="alert-danger" role="alert">{error}</div>}
                        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="forgot-email">Email address</label>
                                <input
                                    id="forgot-email"
                                    className="form-input"
                                    type="email"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    placeholder="you@example.com"
                                    autoComplete="email"
                                    required
                                />
                            </div>
                            <button
                                type="submit"
                                className="btn-primary"
                                style={{ width: '100%', justifyContent: 'center', padding: '11px' }}
                                disabled={loading}
                            >
                                {loading ? 'Sending…' : 'Send reset link'}
                            </button>
                        </form>
                        <div className="login-footer-link">
                            <Link to="/">← Back to sign in</Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

export default ForgotPassword;
