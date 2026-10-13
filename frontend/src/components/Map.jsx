import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import { pointsFromCompact } from '../utils/mapPoints';

function Map() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [points, setPoints] = useState([]);

    const loadMap = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        setStatus('loading');
        try {
            const response = await api.get('/map/points');
            if (!isCurrent()) return;
            const loaded = pointsFromCompact(response.data.fields, response.data.points);
            setPoints(loaded);
            setStatus(loaded.length === 0 ? 'empty' : 'loaded');
        } catch {
            if (isCurrent()) setStatus('error');
        }
    }, []);

    useEffect(() => { loadMap(); }, [token, loadMap]);

    const groups = useMemo(() => [{ name: 'My courses', color: 'red', points }], [points]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 Your Golf Map</div>
                <button className="btn-ghost" onClick={loadMap}>
                    ⟳ Refresh Map
                </button>
            </div>

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'empty' && (
                <p className="map-status">
                    You haven't added any courses yet.{' '}
                    <a href="/course_search" style={{ color: 'var(--primary)' }}>Search for courses to add.</a>
                </p>
            )}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {status === 'loaded' && <CourseMap groups={groups} />}
        </div>
    );
}

export default Map;
