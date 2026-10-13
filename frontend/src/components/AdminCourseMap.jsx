import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Form } from 'react-bootstrap';
import api from '../services/api';
import CourseMap from './CourseMap';
import { pointsFromCompact } from '../utils/mapPoints';

const ALL = '__all__';

// Option values encode the (normalized) state + country pair, since the
// same state code can appear under more than one country.
const optionValue = ({ state, country }) => JSON.stringify([state, country ?? null]);

export default function AdminCourseMap() {
    const activeCallRef = useRef(null);
    const [states, setStates] = useState([]);
    const [statesError, setStatesError] = useState(false);
    const [selection, setSelection] = useState('');
    const [status, setStatus] = useState('idle'); // idle | loading | loaded | error
    const [points, setPoints] = useState([]);

    useEffect(() => {
        let cancelled = false;
        api.get('/admin/courses/states')
            .then(res => { if (!cancelled) setStates(res.data); })
            .catch(() => { if (!cancelled) setStatesError(true); });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        if (!selection) return;
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        let params = {};
        if (selection !== ALL) {
            const [state, country] = JSON.parse(selection);
            // An empty country selects courses with no country, rather than
            // matching this state code across every country.
            params = { state, country: country ?? '' };
        }
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
                    aria-label="State"
                    className="admin-course-map-select"
                    value={selection}
                    onChange={e => setSelection(e.target.value)}
                >
                    <option value="" disabled>Choose a state…</option>
                    {states.map(s => (
                        <option key={optionValue(s)} value={optionValue(s)}>
                            {s.state}{s.country ? `, ${s.country}` : ''} ({s.count.toLocaleString()})
                        </option>
                    ))}
                    <option value={ALL}>All courses — large download</option>
                </Form.Select>
            </div>

            {statesError && <Alert variant="warning">Failed to load the state list.</Alert>}
            {status === 'idle' && <p className="map-status">Pick a state to see its courses.</p>}
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
