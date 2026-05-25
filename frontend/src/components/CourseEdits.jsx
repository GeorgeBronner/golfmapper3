import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Spinner, Table, Badge } from 'react-bootstrap';
import CourseEditsNav from './CourseEditsNav';
import api from '../services/api';

function StatusBadge({ status }) {
    const map = { pending: 'warning', approved: 'success', rejected: 'danger' };
    return <Badge bg={map[status] ?? 'secondary'} text={status === 'pending' ? 'dark' : undefined}>{status}</Badge>;
}

function MyRequests({ refreshKey }) {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        api.get('/course-requests/my-requests')
            .then(res => setRequests(res.data))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [refreshKey]);

    if (loading) return <div className="text-center py-3"><Spinner size="sm" className="me-2" />Loading your requests…</div>;
    if (!requests.length) return <p className="text-muted">No requests submitted yet.</p>;

    return (
        <Table hover responsive size="sm">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Course</th>
                    <th>Submitted</th>
                    <th>Status</th>
                    <th>Admin Note</th>
                </tr>
            </thead>
            <tbody>
                {requests.map(r => (
                    <tr key={r.id}>
                        <td>{r.request_type === 'new_course' ? 'New Course' : 'Location Change'}</td>
                        <td>
                            {r.request_type === 'new_course'
                                ? [r.club_name, r.course_name].filter(Boolean).join(' – ') || '—'
                                : r.course_display_name || `Course #${r.course_id}`}
                        </td>
                        <td className="text-nowrap">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                        <td><StatusBadge status={r.status} /></td>
                        <td className="text-muted" style={{ fontSize: '0.85rem' }}>{r.review_message || '—'}</td>
                    </tr>
                ))}
            </tbody>
        </Table>
    );
}

export default function CourseEditsLayout() {
    const [refreshKey, setRefreshKey] = useState(0);
    const onSubmitted = () => setRefreshKey(k => k + 1);

    return (
        <>
            <CourseEditsNav />
            <div className="p-3">
                <Outlet context={{ onSubmitted }} />

                <hr />
                <h5 className="mb-3">My Requests</h5>
                <MyRequests refreshKey={refreshKey} />
            </div>
        </>
    );
}
