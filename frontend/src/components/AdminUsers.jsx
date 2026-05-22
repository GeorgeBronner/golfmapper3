import React, { useEffect, useState, useCallback } from 'react';
import { Table, Button, Badge, Modal, Form, Alert } from 'react-bootstrap';
import api from '../services/api';

const AdminUsers = () => {
    const [users, setUsers] = useState([]);
    const [alert, setAlert] = useState(null); // { variant, message }
    const [passwordModal, setPasswordModal] = useState(null); // { userId, username }
    const [newPassword, setNewPassword] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const showAlert = (variant, message) => {
        setAlert({ variant, message });
        setTimeout(() => setAlert(null), 3000);
    };

    const loadUsers = useCallback(async () => {
        try {
            const res = await api.get('/admin/users');
            setUsers(res.data);
        } catch {
            showAlert('danger', 'Failed to load users.');
        }
    }, []);

    useEffect(() => { loadUsers(); }, [loadUsers]);

    const toggleRole = async (user) => {
        const newRole = user.role === 'admin' ? 'user' : 'admin';
        try {
            await api.patch(`/admin/users/${user.id}/role`, { role: newRole });
            showAlert('success', `${user.username} is now ${newRole}.`);
            loadUsers();
        } catch {
            showAlert('danger', 'Failed to update role.');
        }
    };

    const openPasswordModal = (user) => {
        setPasswordModal({ userId: user.id, username: user.username });
        setNewPassword('');
    };

    const handlePasswordReset = async (e) => {
        e.preventDefault();
        if (!newPassword) return;
        setSubmitting(true);
        try {
            await api.patch(`/admin/users/${passwordModal.userId}/password`, {
                new_password: newPassword,
            });
            showAlert('success', `Password updated for ${passwordModal.username}.`);
            setPasswordModal(null);
        } catch {
            showAlert('danger', 'Failed to reset password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div>
            <h2 className="mb-4">User Management</h2>

            {alert && (
                <Alert variant={alert.variant} dismissible onClose={() => setAlert(null)}>
                    {alert.message}
                </Alert>
            )}

            <Table hover responsive className="align-middle">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Name</th>
                        <th>Role</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users.map((u) => (
                        <tr key={u.id}>
                            <td>{u.username}</td>
                            <td>{u.email}</td>
                            <td>{u.first_name} {u.last_name}</td>
                            <td>
                                <Badge bg={u.role === 'admin' ? 'danger' : 'secondary'}>
                                    {u.role}
                                </Badge>
                            </td>
                            <td className="d-flex gap-2">
                                <Button
                                    size="sm"
                                    variant={u.role === 'admin' ? 'outline-secondary' : 'outline-primary'}
                                    onClick={() => toggleRole(u)}
                                >
                                    {u.role === 'admin' ? 'Remove Admin' : 'Make Admin'}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline-warning"
                                    onClick={() => openPasswordModal(u)}
                                >
                                    Reset Password
                                </Button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </Table>

            <Modal show={!!passwordModal} onHide={() => setPasswordModal(null)} centered>
                <Modal.Header closeButton>
                    <Modal.Title>Reset Password — {passwordModal?.username}</Modal.Title>
                </Modal.Header>
                <Form onSubmit={handlePasswordReset}>
                    <Modal.Body>
                        <Form.Group>
                            <Form.Label>New Password</Form.Label>
                            <Form.Control
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="Enter new password"
                                required
                                autoFocus
                            />
                        </Form.Group>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={() => setPasswordModal(null)}>
                            Cancel
                        </Button>
                        <Button variant="warning" type="submit" disabled={submitting}>
                            {submitting ? 'Saving…' : 'Reset Password'}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>
        </div>
    );
};

export default AdminUsers;
