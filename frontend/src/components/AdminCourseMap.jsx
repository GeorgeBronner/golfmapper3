import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Form } from 'react-bootstrap';
import api from '../services/api';
import CourseMap from './CourseMap';
import { pointsFromCompact } from '../utils/mapPoints';

const ALL = '__all__';
const US = 'USA';

// Option values are the /courses/points query params, JSON-encoded. An
// empty country selects courses with no country.
const stateValue = state => JSON.stringify({ state, country: US });
const countryValue = country => JSON.stringify({ country: country ?? '' });
const label = (name, count) => `${name} (${count.toLocaleString()})`;

export default function AdminCourseMap() {
    const activeCallRef = useRef(null);
    const [regions, setRegions] = useState({ us_states: [], countries: [] });
    const [regionsError, setRegionsError] = useState(false);
    const [selection, setSelection] = useState('');
    const [status, setStatus] = useState('idle'); // idle | loading | loaded | error
    const [points, setPoints] = useState([]);

    useEffect(() => {
        let cancelled = false;
        api.get('/admin/courses/regions')
            .then(res => { if (!cancelled) setRegions(res.data); })
            .catch(() => { if (!cancelled) setRegionsError(true); });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        if (!selection) return;
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        const params = selection === ALL ? {} : JSON.parse(selection);
        setStatus('loading');
        api.get('/admin/courses/points', { params })
            .then(res => {
                if (!isCurrent()) return;
                setPoints(pointsFromCompact(res.data.fields, res.data.points));
                setStatus('loaded');
            })
            .catch(() => { if (isCurrent()) setStatus('error'); });
    }, [selection]);

    const groups = useMemo(() => [{ name: 'Courses', color: '#e74c3c', points }], [points]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 Course Map</div>
                <Form.Select
                    aria-label="Region"
                    className="admin-course-map-select"
                    value={selection}
                    onChange={e => setSelection(e.target.value)}
                >
                    <option value="" disabled>Choose a state or country…</option>
                    {regions.us_states.length > 0 && (
                        <optgroup label="United States">
                            {regions.us_states.map(s => (
                                <option key={s.state} value={stateValue(s.state)}>{label(s.state, s.count)}</option>
                            ))}
                        </optgroup>
                    )}
                    {regions.countries.length > 0 && (
                        <optgroup label="Countries">
                            {regions.countries.map(c => (
                                <option key={c.country ?? ''} value={countryValue(c.country)}>
                                    {label(c.country ?? 'No country', c.count)}
                                </option>
                            ))}
                        </optgroup>
                    )}
                    <option value={ALL}>All courses — large download</option>
                </Form.Select>
            </div>

            {regionsError && <Alert variant="warning">Failed to load the region list.</Alert>}
            {status === 'idle' && <p className="map-status">Pick a state or country to see its courses.</p>}
            {status === 'loading' && <p className="map-status">Loading courses…</p>}
            {status === 'error' && <p className="map-status">Failed to load courses. Please try again later.</p>}
            {status === 'loaded' && (
                <>
                    <p className="map-status">{points.length.toLocaleString()} courses</p>
                    <CourseMap groups={groups} fitToPoints />
                </>
            )}
        </div>
    );
}
