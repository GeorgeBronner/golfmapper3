import React, { useState, useRef, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Form, Button, Row, Col, Alert, Spinner, Card } from 'react-bootstrap';
import api from '../services/api';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const DEFAULT_CENTER = [39, -98];

function FlyTo({ target }) {
    const map = useMap();
    useEffect(() => { if (target) map.flyTo(target, 14); }, [target, map]);
    return null;
}

function DraggableMarker({ position, setPosition }) {
    const markerRef = useRef(null);
    const eventHandlers = { dragend() { const m = markerRef.current; if (m) setPosition(m.getLatLng()); } };
    return <Marker draggable position={position} eventHandlers={eventHandlers} ref={markerRef} />;
}

function MapClickHandler({ setPosition }) {
    useMapEvents({ click(e) { setPosition(e.latlng); } });
    return null;
}

export default function CourseEditsLocationChange() {
    const { onSubmitted } = useOutletContext();
    const [courseId, setCourseId] = useState('');
    const [course, setCourse] = useState(null);
    const [position, setPosition] = useState(null);
    const [flyTarget, setFlyTarget] = useState(null);
    const [loadAlert, setLoadAlert] = useState(null);
    const [submitAlert, setSubmitAlert] = useState(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleLoad = async e => {
        e.preventDefault();
        if (!courseId) return;
        setLoading(true);
        setLoadAlert(null);
        setCourse(null);
        setSubmitAlert(null);
        setSubmitted(false);
        try {
            const res = await api.get(`/garmin_courses/course/${courseId}`);
            const c = res.data;
            setCourse(c);
            const pos = Number.isFinite(c.latitude) && Number.isFinite(c.longitude)
                ? { lat: c.latitude, lng: c.longitude }
                : null;
            setPosition(pos);
            setFlyTarget(pos);
        } catch (err) {
            setLoadAlert(err.response?.status === 404 ? `Course ID ${courseId} not found.` : 'Failed to load course.');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async e => {
        e.preventDefault();
        if (!course || !position) return;
        setSaving(true);
        setSubmitAlert(null);
        try {
            await api.post('/course-requests/location-change', {
                course_id: course.id,
                latitude: position.lat ?? position[0],
                longitude: position.lng ?? position[1],
            });
            setSubmitted(true);
            onSubmitted();
        } catch (err) {
            const detail = err.response?.data?.detail || 'Failed to submit request.';
            setSubmitAlert({ variant: err.response?.status === 409 ? 'warning' : 'danger', msg: detail });
        } finally {
            setSaving(false);
        }
    };

    const lat = position ? (position.lat ?? position[0]) : null;
    const lng = position ? (position.lng ?? position[1]) : null;

    return (
        <>
            <h5 className="mb-3">Request Location Change</h5>
            <Form onSubmit={handleLoad} className="mb-3">
                <Row className="align-items-end g-2">
                    <Col xs="auto">
                        <Form.Label>Course ID</Form.Label>
                        <Form.Control
                            type="number" min="1" value={courseId}
                            onChange={e => setCourseId(e.target.value)}
                            placeholder="Enter course ID" style={{ width: '160px' }}
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

            {course && !submitted && (
                <>
                    <Card className="mb-3">
                        <Card.Body className="py-2">
                            <strong>{course.display_name}</strong>
                            <span className="text-muted ms-2">{[course.city, course.state, course.country].filter(Boolean).join(', ')}</span>
                        </Card.Body>
                    </Card>

                    {submitAlert && <Alert variant={submitAlert.variant} dismissible onClose={() => setSubmitAlert(null)}>{submitAlert.msg}</Alert>}

                    <p className="text-muted mb-1" style={{ fontSize: '0.85rem' }}>
                        Drag the marker or click anywhere on the map to propose a new location.
                    </p>
                    <Row>
                        <Col md={9}>
                            <MapContainer center={position ? [lat, lng] : DEFAULT_CENTER} zoom={position ? 14 : 4} style={{ height: '460px', width: '100%', borderRadius: '6px' }}>
                                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                                <FlyTo target={flyTarget} />
                                <MapClickHandler setPosition={setPosition} />
                                {position && <DraggableMarker position={position} setPosition={setPosition} />}
                            </MapContainer>
                        </Col>
                        <Col md={3} className="d-flex flex-column justify-content-center">
                            <div className="mb-3">
                                <div className="text-muted mb-1" style={{ fontSize: '0.85rem' }}>Proposed coordinates</div>
                                <div><strong>Lat:</strong> {lat?.toFixed(6)}</div>
                                <div><strong>Lng:</strong> {lng?.toFixed(6)}</div>
                            </div>
                            <Button variant="primary" onClick={handleSubmit} disabled={saving || !position}>
                                {saving ? <><Spinner size="sm" className="me-1" />Submitting…</> : 'Submit Location Change'}
                            </Button>
                        </Col>
                    </Row>
                </>
            )}

            {submitted && (
                <Alert variant="info" className="mt-3">
                    <strong>Request submitted!</strong> An admin will review your location change shortly. Check the table below for status updates.
                    <div className="mt-2">
                        <Button variant="outline-info" size="sm" onClick={() => { setSubmitted(false); setCourse(null); setCourseId(''); setPosition(null); }}>
                            Submit another
                        </Button>
                    </div>
                </Alert>
            )}
        </>
    );
}
