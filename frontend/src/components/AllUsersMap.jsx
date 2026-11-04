import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import { pointsFromCompact, USER_COLORS, RANKING_COLORS } from '../utils/mapPoints';

const layerKey = (listId, editionId) => `${listId}:${editionId}`;

// One ranking edition as a map group, plus each course's rank for the popups.
async function loadLayer(list, listIndex, editionId) {
    const { data } = await api.get(`/map/rankings/${list.id}/points`, { params: { edition_id: editionId } });
    const name = `${list.name} ${data.edition}`;
    const points = pointsFromCompact(data.fields, data.points);
    const ranks = {};
    points.forEach(p => { ranks[p.id] = { rank: p.rank, label: name, tied: p.rank_label }; });
    return {
        group: { name, color: RANKING_COLORS[listIndex % RANKING_COLORS.length], points },
        ranks,
    };
}

function AllUsersMap() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [userGroups, setUserGroups] = useState([]);
    const [lists, setLists] = useState([]);
    // Per list: whether its layer is on and which edition. The first list starts on.
    const [layers, setLayers] = useState({});
    // `${listId}:${editionId}` -> { group, ranks } once loaded.
    const [loaded, setLoaded] = useState({});
    const requested = useRef(new Set());
    // Bumped on every refresh so the layer effect runs again even when the
    // rankings call failed and `lists`/`layers` therefore did not change.
    const [refreshCount, setRefreshCount] = useState(0);
    // Bumped on every (re)load so a layer response from before a refresh is ignored.
    const generation = useRef(0);
    // Keys of layers whose last fetch failed, so the bar can say so.
    const [failed, setFailed] = useState(() => new Set());

    const loadMap = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        setStatus('loading');
        try {
            // The ranking lists are extras: the map still works without them.
            const [{ data }, fetchedLists] = await Promise.all([
                api.get('/map/all_points'),
                api.get('/rankings').then(r => (Array.isArray(r.data) ? r.data : [])).catch(() => null),
            ]);
            if (!isCurrent()) return;
            setUserGroups(data.users.map((u, i) => ({
                name: u.username,
                color: USER_COLORS[i % USER_COLORS.length],
                points: pointsFromCompact(data.fields, u.points),
            })));
            // If only the rankings call failed, keep the bar and choices we already have.
            if (fetchedLists) {
                const usable = fetchedLists.filter(l => l.editions?.length);
                setLists(usable);
                setLayers(prev => Object.fromEntries(usable.map((l, i) => {
                    const old = prev[l.id];
                    const stillThere = old && l.editions.some(e => e.id === old.editionId);
                    return [l.id, stillThere ? old : { on: old ? old.on : i === 0, editionId: l.editions[0].id }];
                })));
            }
            generation.current += 1;
            requested.current = new Set();  // a refresh reloads the layers too
            setLoaded({});
            setFailed(new Set());
            setRefreshCount(n => n + 1);
            setStatus('loaded');
        } catch {
            if (isCurrent()) setStatus('error');
        }
    }, []);

    useEffect(() => { loadMap(); }, [token, loadMap]);

    // Fetch each switched-on layer once; a failure just leaves that layer out.
    useEffect(() => {
        lists.forEach((list, i) => {
            const layer = layers[list.id];
            if (!layer?.on) return;
            const key = layerKey(list.id, layer.editionId);
            if (requested.current.has(key)) return;
            requested.current.add(key);
            const gen = generation.current;
            setFailed(prev => { if (!prev.has(key)) return prev; const next = new Set(prev); next.delete(key); return next; });
            loadLayer(list, i, layer.editionId)
                .then(result => { if (gen === generation.current) setLoaded(prev => ({ ...prev, [key]: result })); })
                .catch(() => {
                    if (gen !== generation.current) return;
                    requested.current.delete(key);  // toggling the layer off and on retries
                    setFailed(prev => new Set(prev).add(key));
                });
        });
    }, [lists, layers, refreshCount]);

    const { groups, ranks } = useMemo(() => {
        const rankingGroups = [];
        const ranks = {};
        lists.forEach(list => {
            const layer = layers[list.id];
            const result = layer?.on && loaded[layerKey(list.id, layer.editionId)];
            if (!result) return;
            rankingGroups.push(result.group);
            Object.entries(result.ranks).forEach(([id, r]) => { (ranks[id] ??= []).push(r); });
        });
        return { groups: [...userGroups, ...rankingGroups], ranks };
    }, [lists, layers, loaded, userGroups]);

    const setLayer = (listId, patch) => setLayers(prev => ({ ...prev, [listId]: { ...prev[listId], ...patch } }));

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 All Users Map</div>
                <button className="btn-ghost" onClick={loadMap}>
                    ⟳ Refresh Map
                </button>
            </div>

            {status === 'loaded' && lists.length > 0 && (
                <div className="map-rankings-bar">
                    <strong>Rankings</strong>
                    {lists.map(list => (
                        <div key={list.id} className="map-rankings-layer">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={!!layers[list.id]?.on}
                                    onChange={e => setLayer(list.id, { on: e.target.checked })}
                                />{' '}
                                {list.name}
                            </label>
                            <select
                                aria-label={`${list.name} edition`}
                                value={layers[list.id]?.editionId ?? ''}
                                onChange={e => setLayer(list.id, { editionId: Number(e.target.value) })}
                            >
                                {list.editions.map(ed => <option key={ed.id} value={ed.id}>{ed.label}</option>)}
                            </select>
                            {layers[list.id]?.on && failed.has(layerKey(list.id, layers[list.id].editionId)) && (
                                <span role="alert">⚠ couldn't load</span>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {status === 'loaded' && <CourseMap groups={groups} showLegend ranks={ranks} />}
        </div>
    );
}

export default AllUsersMap;
