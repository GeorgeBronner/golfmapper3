import React, { useEffect, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import { pointsFromCompact, USER_COLORS } from '../utils/mapPoints';
import useCurrentRanks from '../utils/useCurrentRanks';

function AllUsersMap() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [groups, setGroups] = useState([]);
    const ranks = useCurrentRanks();

    const loadMap = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        setStatus('loading');
        try {
            const { data } = await api.get('/map/all_points');
            if (!isCurrent()) return;
            setGroups(data.users.map((u, i) => ({
                name: u.username,
                color: USER_COLORS[i % USER_COLORS.length],
                points: pointsFromCompact(data.fields, u.points),
            })));
            setStatus('loaded');
        } catch {
            if (isCurrent()) setStatus('error');
        }
    }, []);

    useEffect(() => { loadMap(); }, [token, loadMap]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 All Users Map</div>
                <button className="btn-ghost" onClick={loadMap}>
                    ⟳ Refresh Map
                </button>
            </div>

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {status === 'loaded' && <CourseMap groups={groups} showLegend ranks={ranks} />}
        </div>
    );
}

export default AllUsersMap;
