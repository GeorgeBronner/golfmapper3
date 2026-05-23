import React, { useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Form, Button, Row, Col, Alert, Spinner } from 'react-bootstrap';
import api from '../services/api';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const EMPTY_FORM = { club_name: '', course_name: '', address: '', city: '', state: '', country: '' };

function LocationPicker({ position, setPosition, setForm }) {
    const abortRef = useRef(null);
    useMapEvents({
        click(e) {
            const { lat, lng } = e.latlng;
            setPosition([lat, lng]);
            if (abortRef.current) abortRef.current.abort();
            const controller = new AbortController();
            abortRef.current = controller;
            fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`, { signal: controller.signal })
                .then(r => r.json())
                .then(data => {
                    const a = data.address || {};
                    setForm(prev => ({
                        ...prev,
                        city: a.city || a.town || a.village || a.hamlet || '',
                        state: a.state || '',
                        country: a.country || '',
                        address: a.road ? `${a.house_number ? a.house_number + ' ' : ''}${a.road}` : '',
                    }));
                })
                .catch(err => { if (err.name !== 'AbortError') console.error(err); });
        },
    });
    return position ? <Marker position={position} /> : null;
}

export default function AdminAddCourse() {
    const [form, setForm] = useState(EMPTY_FORM);
    const [position, setPosition] = useState(null);
    const [alert, setAlert] = useState(null);
    const [saving, setSaving] = useState(false);

    const handleField = e => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

    const handleSubmit = async e => {
        e.preventDefault();
        if (!position) { setAlert({ variant: 'warning', msg: 'Click the map to set a location first.' }); return; }
        setSaving(true);
        setAlert(null);
        try {
            const res = await api.post('/admin/courses', {
                ...form,
                latitude: position[0],
                longitude: position[1],
            });
            setAlert({ variant: 'success', msg: `Course "${res.data.display_name}" (ID ${res.data.id}) added successfully.` });
            setForm(EMPTY_FORM);
            setPosition(null);
        } catch (err) {
            setAlert({ variant: 'danger', msg: err.response?.data?.detail || 'Failed to add course.' });
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="p-3">
            <h4 className="mb-3">Add Course</h4>
            {alert && <Alert variant={alert.variant} dismissible onClose={() => setAlert(null)}>{alert.msg}</Alert>}
            <Row>
                <Col md={5}>
                    <Form onSubmit={handleSubmit}>
                        <Form.Group className="mb-2">
                            <Form.Label>Club Name</Form.Label>
                            <Form.Control name="club_name" value={form.club_name} onChange={handleField} placeholder="e.g. Augusta National" />
                        </Form.Group>
                        <Form.Group className="mb-2">
                            <Form.Label>Course Name</Form.Label>
                            <Form.Control name="course_name" value={form.course_name} onChange={handleField} placeholder="e.g. Championship Course" />
                        </Form.Group>
                        <Form.Group className="mb-2">
                            <Form.Label>Address</Form.Label>
                            <Form.Control name="address" value={form.address} onChange={handleField} placeholder="Street address" />
                        </Form.Group>
                        <Form.Group className="mb-2">
                            <Form.Label>City</Form.Label>
                            <Form.Control name="city" value={form.city} onChange={handleField} />
                        </Form.Group>
                        <Form.Group className="mb-2">
                            <Form.Label>State / Province</Form.Label>
                            <Form.Control name="state" value={form.state} onChange={handleField} />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Country</Form.Label>
                            <Form.Control name="country" value={form.country} onChange={handleField} />
                        </Form.Group>
                        <div className="mb-3 text-muted" style={{ fontSize: '0.9rem' }}>
                            {position
                                ? <><strong>Lat:</strong> {position[0].toFixed(6)} &nbsp; <strong>Lng:</strong> {position[1].toFixed(6)}</>
                                : 'Click the map to set coordinates'}
                        </div>
                        <Button type="submit" variant="primary" disabled={saving || !position}>
                            {saving ? <><Spinner size="sm" className="me-1" />Saving…</> : 'Add Course'}
                        </Button>
                    </Form>
                </Col>
                <Col md={7}>
                    <p className="text-muted mb-1" style={{ fontSize: '0.85rem' }}>Click anywhere on the map to set the course location. Address fields will auto-fill.</p>
                    <MapContainer center={[39, -98]} zoom={4} style={{ height: '480px', width: '100%', borderRadius: '6px' }}>
                        <TileLayer
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <LocationPicker position={position} setPosition={setPosition} setForm={setForm} />
                    </MapContainer>
                </Col>
            </Row>
        </div>
    );
}
