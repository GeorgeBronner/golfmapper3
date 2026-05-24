import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../services/api';

function ResetPassword() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');

        if (password.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }
        if (password !== confirm) {
            setError('Passwords do not match.');
            return;
        }

        setLoading(true);
        api.post('/auth/reset-password', { token, new_password: password })
            .then(() => setSuccess(true))
            .catch(err => {
                const detail = err.response?.data?.detail;
                setError(detail || 'Something went wrong. Please try again.');
            })
            .finally(() => setLoading(false));
    };

    if (!token) {
        return (
            <div className="login-shell">
                <div className="login-hero">
                    <div className="login-hero-logo">⛳ GolfMapper</div>
                </div>
                <div className="login-form-panel">
                    <div className="login-form-title">Invalid link</div>
                    <div className="alert-danger" role="alert">This reset link is missing a token.</div>
                    <div className="login-footer-link"><Link to="/">← Back to sign in</Link></div>
                </div>
            </div>
        );
    }

    return (
        <div className="login-shell">
            <div className="login-hero">
                <div className="login-hero-logo">⛳ GolfMapper</div>
                <div>
                    <div className="login-hero-tagline">
                        Set a new<br />password
                    </div>
                    <div className="login-hero-sub">
                        Choose something strong and memorable.
                    </div>
                </div>
            </div>

            <div className="login-form-panel">
                <div>
                    <div className="login-form-title">New password</div>
                    <div className="login-form-subtitle">Minimum 8 characters</div>
                </div>

                {success ? (
                    <div>
                        <div className="alert-success" role="alert">
                            Password updated! You can now sign in with your new password.
                        </div>
                        <div className="login-footer-link" style={{ marginTop: '1rem' }}>
                            <Link to="/">Sign in →</Link>
                        </div>
                    </div>
                ) : (
                    <>
                        {error && <div className="alert-danger" role="alert">{error}</div>}
                        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="reset-password">New password</label>
                                <input
                                    id="reset-password"
                                    className="form-input"
                                    type="password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    autoComplete="new-password"
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label" htmlFor="reset-confirm">Confirm password</label>
                                <input
                                    id="reset-confirm"
                                    className="form-input"
                                    type="password"
                                    value={confirm}
                                    onChange={e => setConfirm(e.target.value)}
                                    placeholder="••••••••"
                                    autoComplete="new-password"
                                    required
                                />
                            </div>
                            <button
                                type="submit"
                                className="btn-primary"
                                style={{ width: '100%', justifyContent: 'center', padding: '11px' }}
                                disabled={loading}
                            >
                                {loading ? 'Saving…' : 'Set new password'}
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

export default ResetPassword;
