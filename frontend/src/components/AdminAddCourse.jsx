import React, { useState, useRef } from 'react';
import { MapContainer, Marker, useMapEvents } from 'react-leaflet';
import BaseLayers from './BaseLayers';
import 'leaflet/dist/leaflet.css';
import { Form, Button, Row, Col, Alert, Spinner } from 'react-bootstrap';
import api from '../services/api';
import { nominatimToGeoFields, validateGeoFields } from '../utils/geoLookup';
import { CountrySelect, StateInput } from './GeoCodeInputs';
import '../utils/leafletIcons';

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
                    const { city, state, country } = nominatimToGeoFields(a);
                    setForm(prev => ({
                        ...prev,
                        city,
                        state,
                        country,
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
    const [checkGeo, setCheckGeo] = useState(false);

    const handleField = e => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const geoErrors = checkGeo ? validateGeoFields(form) : {};

    const handleSubmit = async e => {
        e.preventDefault();
        if (!position) { setAlert({ variant: 'warning', msg: 'Click the map to set a location first.' }); return; }
        setCheckGeo(true);
        if (Object.keys(validateGeoFields(form)).length) { setAlert({ variant: 'warning', msg: 'Fix the country/state codes before saving.' }); return; }
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
                            <StateInput value={form.state} onChange={handleField} error={geoErrors.state} />
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Country</Form.Label>
                            <CountrySelect value={form.country} onChange={handleField} error={geoErrors.country} />
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
                        <BaseLayers defaultLayer="satellite" />
                        <LocationPicker position={position} setPosition={setPosition} setForm={setForm} />
                    </MapContainer>
                </Col>
            </Row>
        </div>
    );
}
