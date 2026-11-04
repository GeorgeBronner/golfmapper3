import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import RankingLayersBar from './RankingLayersBar';
import { pointsFromCompact, PLAYED_COLOR } from '../utils/mapPoints';
import useCurrentRanks from '../utils/useCurrentRanks';
import useRankingLayers from '../utils/useRankingLayers';

function Map() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [points, setPoints] = useState([]);
    const currentRanks = useCurrentRanks();
    // Layers start off here so the map looks as it always did until one is ticked.
    const rankingLayers = useRankingLayers({ firstOn: false });
    const { refresh: refreshLayers } = rankingLayers;

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

    const refresh = () => { loadMap(); refreshLayers(); };

    // Draw order, bottom to top: each ranking layer's unplayed courses, "My courses", then the
    // ranked courses the user has played in a third color, so a played course stands out over
    // the red dot underneath it instead of being hidden by the layer.
    const groups = useMemo(() => {
        const played = new Set(points.map(p => p.id));
        const unplayedGroups = [];
        const playedGroups = [];
        rankingLayers.groups.forEach(group => {
            const unplayed = group.points.filter(p => !played.has(p.id));
            // A layer the user has fully played has no unplayed dots, so no empty legend entry.
            if (unplayed.length > 0) unplayedGroups.push({ ...group, points: unplayed });
            const mine = group.points.filter(p => played.has(p.id));
            if (mine.length > 0) playedGroups.push({ name: `${group.name} · played`, color: PLAYED_COLOR, points: mine });
        });
        return [...unplayedGroups, { name: 'My courses', color: 'red', points }, ...playedGroups];
    }, [points, rankingLayers.groups]);

    const hasLayers = rankingLayers.groups.length > 0;
    // With layers on, popups list the rank in each; otherwise the current US Public rank as before.
    const ranks = hasLayers ? rankingLayers.ranks : currentRanks;
    const showMap = status === 'loaded' || status === 'empty';

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 Your Golf Map</div>
                <button className="btn-ghost" onClick={refresh}>
                    ⟳ Refresh Map
                </button>
            </div>

            {showMap && <RankingLayersBar ui={rankingLayers.ui} />}

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'empty' && (
                <p className="map-status">
                    You haven't added any courses yet.{' '}
                    <a href="/course_search" style={{ color: 'var(--primary)' }}>Search for courses to add.</a>
                </p>
            )}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {showMap && (
                <CourseMap groups={groups} ranks={ranks} showLegend={hasLayers} focusPoints={rankingLayers.focusPoints} />
            )}
        </div>
    );
}

export default Map;
