import React, { useState } from 'react';
import { useAuth } from './AuthProvider';
import api from '../services/api';

function UserProfile() {
    const { username } = useAuth();
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [alert, setAlert] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const showAlert = (type, message) => {
        setAlert({ type, message });
        setTimeout(() => setAlert(null), 4000);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            showAlert('danger', 'New passwords do not match.');
            return;
        }
        if (newPassword.length < 6) {
            showAlert('danger', 'New password must be at least 6 characters.');
            return;
        }
        setSubmitting(true);
        try {
            await api.put('/user/password', {
                password: currentPassword,
                new_password: newPassword,
            });
            showAlert('success', 'Password updated successfully.');
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (err) {
            const detail = err.response?.data?.detail;
            showAlert('danger', detail === 'Error on password verification'
                ? 'Current password is incorrect.'
                : 'Failed to update password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">My Profile</div>
                    <div className="page-subtitle">Manage your account settings</div>
                </div>
            </div>

            <div className="form-card">
                <div style={{ marginBottom: '20px' }}>
                    <div className="form-label" style={{ marginBottom: '2px' }}>Username</div>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>{username}</div>
                </div>

                <div style={{ height: '1px', background: 'var(--border)', margin: '20px 0' }} />

                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px' }}>
                    Change Password
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Current Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={currentPassword}
                            onChange={e => setCurrentPassword(e.target.value)}
                            placeholder="Enter current password"
                            required
                            autoComplete="current-password"
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">New Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            placeholder="Enter new password"
                            required
                            autoComplete="new-password"
                            minLength={6}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Confirm New Password</label>
                        <input
                            type="password"
                            className="form-input"
                            value={confirmPassword}
                            onChange={e => setConfirmPassword(e.target.value)}
                            placeholder="Confirm new password"
                            required
                            autoComplete="new-password"
                        />
                    </div>

                    {alert && (
                        <div className={`alert-${alert.type}`}>{alert.message}</div>
                    )}

                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={submitting}
                        style={{ marginTop: '8px' }}
                    >
                        {submitting ? 'Saving…' : 'Update Password'}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default UserProfile;
