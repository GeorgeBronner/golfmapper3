import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Row, Col, Card, Badge, Button, Form, Spinner, Alert } from 'react-bootstrap';
import api from '../services/api';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

// Blue marker for original location
const blueIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    iconRetinaUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
    shadowUrl: markerShadow,
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

// Red marker for proposed location
const redIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    iconRetinaUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: markerShadow,
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

function StatusBadge({ status }) {
    const map = { pending: 'warning', approved: 'success', rejected: 'danger' };
    return <Badge bg={map[status] ?? 'secondary'} text={status === 'pending' ? 'dark' : undefined}>{status}</Badge>;
}

// ── Mini map for new course ───────────────────────────────────────────────────

function NewCourseMap({ lat, lng }) {
    return (
        <MapContainer center={[lat, lng]} zoom={12} style={{ height: '200px', borderRadius: '6px' }} zoomControl={false} dragging={false} scrollWheelZoom={false}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Marker position={[lat, lng]} />
        </MapContainer>
    );
}

// ── Mini map for location change (before + after) ─────────────────────────────

function LocationChangeMap({ origLat, origLng, newLat, newLng }) {
    const midLat = (origLat + newLat) / 2;
    const midLng = (origLng + newLng) / 2;
    return (
        <MapContainer center={[midLat, midLng]} zoom={11} style={{ height: '200px', borderRadius: '6px' }} zoomControl={false} dragging={false} scrollWheelZoom={false}>
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Marker position={[origLat, origLng]} icon={blueIcon}>
                <Tooltip permanent direction="top" offset={[0, -40]}>Original</Tooltip>
            </Marker>
            <Marker position={[newLat, newLng]} icon={redIcon}>
                <Tooltip permanent direction="top" offset={[0, -40]}>Proposed</Tooltip>
            </Marker>
        </MapContainer>
    );
}

// ── Request card ──────────────────────────────────────────────────────────────

function RequestCard({ req, onAction }) {
    const [rejecting, setRejecting] = useState(false);
    const [rejectMsg, setRejectMsg] = useState('');
    const [busy, setBusy] = useState(false);
    const [toast, setToast] = useState(null);

    const handleApprove = async () => {
        setBusy(true);
        try {
            await api.post(`/course-requests/admin/${req.id}/approve`);
            onAction(req.id, 'approved');
        } catch (err) {
            setToast(err.response?.data?.detail || 'Failed to approve.');
        } finally {
            setBusy(false);
        }
    };

    const handleReject = async () => {
        if (!rejectMsg.trim()) return;
        setBusy(true);
        try {
            await api.post(`/course-requests/admin/${req.id}/reject`, { message: rejectMsg });
            onAction(req.id, 'rejected');
        } catch (err) {
            setToast(err.response?.data?.detail || 'Failed to reject.');
        } finally {
            setBusy(false);
        }
    };

    const isNew = req.request_type === 'new_course';
    const courseName = isNew
        ? [req.club_name, req.course_name].filter(Boolean).join(' – ') || 'Unnamed Course'
        : req.course_display_name || `Course #${req.course_id}`;

    return (
        <Card className="mb-3">
            <Card.Header className="d-flex justify-content-between align-items-center">
                <span><strong>{courseName}</strong></span>
                <div className="d-flex align-items-center gap-2">
                    <StatusBadge status={req.status} />
                    {req.status === 'approved' && req.request_type === 'new_course' && req.approved_course_id && (
                        <span className="text-muted" style={{ fontSize: '0.8rem' }}>Course ID: {req.approved_course_id}</span>
                    )}
                    <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                        {req.created_at ? new Date(req.created_at).toLocaleDateString() : ''}
                    </span>
                </div>
            </Card.Header>
            <Card.Body>
                {toast && <Alert variant="danger" dismissible onClose={() => setToast(null)} className="mb-2">{toast}</Alert>}
                <Row>
                    <Col md={5}>
                        {isNew ? (
                            <>
                                <div className="mb-2" style={{ fontSize: '0.9rem' }}>
                                    {req.address && <div><strong>Address:</strong> {req.address}</div>}
                                    <div>{[req.city, req.state, req.country].filter(Boolean).join(', ')}</div>
                                    <div className="text-muted mt-1">
                                        <strong>Lat:</strong> {req.latitude?.toFixed(6)} &nbsp;
                                        <strong>Lng:</strong> {req.longitude?.toFixed(6)}
                                    </div>
                                </div>
                                <NewCourseMap lat={req.latitude} lng={req.longitude} />
                            </>
                        ) : (
                            <>
                                <table className="table table-sm table-borderless mb-2" style={{ fontSize: '0.85rem' }}>
                                    <tbody>
                                        <tr>
                                            <td className="text-muted">Original lat</td>
                                            <td>{req.original_latitude?.toFixed(6)}</td>
                                            <td className="text-muted">New lat</td>
                                            <td>{req.latitude?.toFixed(6)}</td>
                                        </tr>
                                        <tr>
                                            <td className="text-muted">Original lng</td>
                                            <td>{req.original_longitude?.toFixed(6)}</td>
                                            <td className="text-muted">New lng</td>
                                            <td>{req.longitude?.toFixed(6)}</td>
                                        </tr>
                                    </tbody>
                                </table>
                                {req.original_latitude != null && req.original_longitude != null ? (
                                    <LocationChangeMap
                                        origLat={req.original_latitude} origLng={req.original_longitude}
                                        newLat={req.latitude} newLng={req.longitude}
                                    />
                                ) : (
                                    <NewCourseMap lat={req.latitude} lng={req.longitude} />
                                )}
                            </>
                        )}
                    </Col>
                    <Col md={7}>
                        {req.review_message && (
                            <Alert variant="secondary" className="mb-2" style={{ fontSize: '0.85rem' }}>
                                <strong>Admin note:</strong> {req.review_message}
                            </Alert>
                        )}

                        {req.status === 'pending' && (
                            <div className="mt-2">
                                <div className="d-flex gap-2 mb-2">
                                    <Button variant="success" size="sm" disabled={busy} onClick={handleApprove}>
                                        {busy && !rejecting ? <Spinner size="sm" className="me-1" /> : null}
                                        Approve
                                    </Button>
                                    <Button variant="outline-danger" size="sm" disabled={busy} onClick={() => setRejecting(r => !r)}>
                                        Reject…
                                    </Button>
                                </div>
                                {rejecting && (
                                    <div>
                                        <Form.Control
                                            as="textarea" rows={2} size="sm"
                                            placeholder="Reason for rejection (required)"
                                            value={rejectMsg}
                                            onChange={e => setRejectMsg(e.target.value)}
                                            className="mb-2"
                                        />
                                        <Button variant="danger" size="sm" disabled={busy || !rejectMsg.trim()} onClick={handleReject}>
                                            {busy ? <Spinner size="sm" className="me-1" /> : null}
                                            Confirm Reject
                                        </Button>
                                        <Button variant="link" size="sm" onClick={() => { setRejecting(false); setRejectMsg(''); }}>
                                            Cancel
                                        </Button>
                                    </div>
                                )}
                            </div>
                        )}
                    </Col>
                </Row>
            </Card.Body>
        </Card>
    );
}

// ── Section (new courses or location changes) ─────────────────────────────────

function RequestSection({ title, type, requests, onAction }) {
    const filtered = requests.filter(r => r.request_type === type);
    if (!filtered.length) return <p className="text-muted">No {title.toLowerCase()} at this time.</p>;
    return (
        <>
            <h6 className="mb-3">{title} <Badge bg="secondary" className="ms-1">{filtered.length}</Badge></h6>
            {filtered.map(r => <RequestCard key={r.id} req={r} onAction={onAction} />)}
        </>
    );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function AdminReviewRequests() {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [pendingOnly, setPendingOnly] = useState(true);
    const [error, setError] = useState(null);
    const fetchSeq = useRef(0);

    const fetchRequests = (pendingOnlyFlag) => {
        const seq = ++fetchSeq.current;
        setLoading(true);
        setError(null);
        api.get(`/course-requests/admin/all?pending_only=${pendingOnlyFlag}`)
            .then(res => { if (seq === fetchSeq.current) setRequests(res.data); })
            .catch(err => { if (seq === fetchSeq.current) setError(err.response?.data?.detail || 'Failed to load requests.'); })
            .finally(() => { if (seq === fetchSeq.current) setLoading(false); });
    };

    useEffect(() => { fetchRequests(pendingOnly); }, [pendingOnly]);

    const handleAction = (id, newStatus) => {
        setRequests(prev =>
            pendingOnly
                ? prev.filter(r => r.id !== id)
                : prev.map(r => r.id === id ? { ...r, status: newStatus } : r)
        );
    };

    return (
        <div className="p-3">
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h4 className="mb-0">Review User Requests</h4>
                <Form.Check
                    type="switch"
                    id="pending-only-toggle"
                    label="Pending only"
                    checked={pendingOnly}
                    onChange={e => setPendingOnly(e.target.checked)}
                />
            </div>

            {error && <Alert variant="danger">{error}</Alert>}

            {loading ? (
                <div className="text-center py-4"><Spinner /> Loading requests…</div>
            ) : (
                <Row>
                    <Col md={6} className="mb-4">
                        <h5 className="border-bottom pb-2 mb-3">New Course Requests</h5>
                        <RequestSection title="New Courses" type="new_course" requests={requests} onAction={handleAction} />
                    </Col>
                    <Col md={6} className="mb-4">
                        <h5 className="border-bottom pb-2 mb-3">Location Change Requests</h5>
                        <RequestSection title="Location Changes" type="location_change" requests={requests} onAction={handleAction} />
                    </Col>
                </Row>
            )}
        </div>
    );
}
