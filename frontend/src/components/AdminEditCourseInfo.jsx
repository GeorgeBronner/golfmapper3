import React, { useState } from 'react';
import { Form, Button, Row, Col, Alert, Spinner, Card } from 'react-bootstrap';
import api from '../services/api';

const FIELDS = [
    { name: 'club_name',   label: 'Club Name' },
    { name: 'course_name', label: 'Course Name' },
    { name: 'address',     label: 'Address' },
    { name: 'city',        label: 'City' },
    { name: 'state',       label: 'State / Province' },
    { name: 'country',     label: 'Country' },
];

export default function AdminEditCourseInfo() {
    const [courseId, setCourseId] = useState('');
    const [course, setCourse] = useState(null);
    const [form, setForm] = useState({});
    const [loadAlert, setLoadAlert] = useState(null);
    const [saveAlert, setSaveAlert] = useState(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleLoad = async e => {
        e.preventDefault();
        if (!courseId) return;
        setLoading(true);
        setLoadAlert(null);
        setCourse(null);
        setSaveAlert(null);
        try {
            const res = await api.get(`/garmin_courses/course/${courseId}`);
            const c = res.data;
            setCourse(c);
            setForm({
                club_name:   c.club_name   ?? '',
                course_name: c.course_name ?? '',
                address:     c.address     ?? '',
                city:        c.city        ?? '',
                state:       c.state       ?? '',
                country:     c.country     ?? '',
            });
        } catch (err) {
            setLoadAlert(err.response?.status === 404 ? `Course ID ${courseId} not found.` : 'Failed to load course.');
        } finally {
            setLoading(false);
        }
    };

    const handleField = e => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const handleSave = async e => {
        e.preventDefault();
        if (!course) return;
        setSaving(true);
        setSaveAlert(null);
        try {
            const res = await api.put(`/admin/courses/${course.id}/info`, form);
            setCourse(res.data);
            setSaveAlert({ variant: 'success', msg: 'Course information updated successfully.' });
        } catch (err) {
            setSaveAlert({ variant: 'danger', msg: err.response?.data?.detail || 'Failed to save changes.' });
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!course) return;
        const confirmed = window.confirm(
            `Delete "${course.display_name}" (ID ${course.id})?\n\nThis will permanently remove the course and all associated user records. This cannot be undone.`
        );
        if (!confirmed) return;
        setDeleting(true);
        setSaveAlert(null);
        try {
            await api.delete(`/admin/courses/${course.id}`);
            setCourse(null);
            setCourseId('');
            setForm({});
            setSaveAlert({ variant: 'success', msg: `Course "${course.display_name}" deleted successfully.` });
        } catch (err) {
            setSaveAlert({ variant: 'danger', msg: err.response?.data?.detail || 'Failed to delete course.' });
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="p-3">
            <h4 className="mb-3">Edit Course Information</h4>

            <Form onSubmit={handleLoad} className="mb-3">
                <Row className="align-items-end g-2">
                    <Col xs="auto">
                        <Form.Label>Course ID</Form.Label>
                        <Form.Control
                            type="number" min="1" value={courseId}
                            onChange={e => setCourseId(e.target.value)}
                            placeholder="Enter course ID"
                            style={{ width: '160px' }}
                        />
                    </Col>
                    <Col xs="auto">
                        <Button type="submit" variant="secondary" disabled={loading || !courseId}>
                            {loading ? <><Spinner size="sm" className="me-1" />Loading…</> : 'Load Course'}
                        </Button>
                    </Col>
                </Row>
                {loadAlert && <Alert variant="warning" className="mt-2 mb-0">{loadAlert}</Alert>}
            </Form>

            {saveAlert && !course && (
                <Alert variant={saveAlert.variant} dismissible onClose={() => setSaveAlert(null)}>
                    {saveAlert.msg}
                </Alert>
            )}

            {course && (
                <>
                    <Card className="mb-3">
                        <Card.Body className="py-2">
                            <strong>{course.display_name}</strong>
                            <span className="text-muted ms-2">{[course.city, course.state, course.country].filter(Boolean).join(', ')}</span>
                            <span className="text-muted ms-3" style={{ fontSize: '0.85rem' }}>ID: {course.id}</span>
                        </Card.Body>
                    </Card>

                    {saveAlert && (
                        <Alert variant={saveAlert.variant} dismissible onClose={() => setSaveAlert(null)}>
                            {saveAlert.msg}
                        </Alert>
                    )}

                    <Form onSubmit={handleSave}>
                        <Row>
                            {FIELDS.map(({ name, label }) => (
                                <Col md={6} key={name} className="mb-3">
                                    <Form.Group>
                                        <Form.Label>{label}</Form.Label>
                                        <Form.Control
                                            name={name}
                                            value={form[name] ?? ''}
                                            onChange={handleField}
                                            placeholder={label}
                                        />
                                    </Form.Group>
                                </Col>
                            ))}
                        </Row>

                        <div className="d-flex justify-content-between align-items-center mt-2">
                            <Button type="submit" variant="primary" disabled={saving}>
                                {saving ? <><Spinner size="sm" className="me-1" />Saving…</> : 'Save Changes'}
                            </Button>

                            <Button
                                type="button"
                                variant="danger"
                                disabled={deleting}
                                onClick={handleDelete}
                            >
                                {deleting ? <><Spinner size="sm" className="me-1" />Deleting…</> : '🗑 Delete Course'}
                            </Button>
                        </div>
                    </Form>
                </>
            )}
        </div>
    );
}
