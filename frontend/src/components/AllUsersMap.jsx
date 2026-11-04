import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import RankingLayersBar from './RankingLayersBar';
import { pointsFromCompact, USER_COLORS } from '../utils/mapPoints';
import useRankingLayers from '../utils/useRankingLayers';

function AllUsersMap() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [userGroups, setUserGroups] = useState([]);
    const rankingLayers = useRankingLayers({ firstOn: true });
    const { refresh: refreshLayers } = rankingLayers;

    const loadMap = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        setStatus('loading');
        try {
            const { data } = await api.get('/map/all_points');
            if (!isCurrent()) return;
            setUserGroups(data.users.map((u, i) => ({
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

    const refresh = () => { loadMap(); refreshLayers(); };

    // Ranking layers are drawn after (on top of) the users' groups.
    const groups = useMemo(() => [...userGroups, ...rankingLayers.groups], [userGroups, rankingLayers.groups]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 All Users Map</div>
                <button className="btn-ghost" onClick={refresh}>
                    ⟳ Refresh Map
                </button>
            </div>

            {status === 'loaded' && <RankingLayersBar ui={rankingLayers.ui} />}

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {status === 'loaded' && (
                <CourseMap groups={groups} showLegend ranks={rankingLayers.ranks} focusPoints={rankingLayers.focusPoints} />
            )}
        </div>
    );
}

export default AllUsersMap;
