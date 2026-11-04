import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';
import CourseMap from './CourseMap';
import { pointsFromCompact, USER_COLORS, RANKING_COLORS, STATE_RANKING_COLOR } from '../utils/mapPoints';

// Each state's Best in State list is its own ranking list with this scope prefix.
// They get one "Best in State" control instead of a checkbox apiece.
const STATE_SCOPE_PREFIX = 'us-state-';
const isStateList = list => list.scope?.startsWith(STATE_SCOPE_PREFIX);
const stateName = list => list.name.replace(/^Best Courses in /, '');
const ALL_STATES = 'ALL';

const layerKey = (listId, editionId) => `${listId}:${editionId}`;

// A loaded layer is { group, ranks }: the map group plus each course's ranks for the popups.
function toLayer(name, color, points, rankLabel) {
    const ranks = {};
    points.forEach(p => { ranks[p.id] = { rank: p.rank, label: rankLabel(p), tied: p.rank_label }; });
    return { group: { name, color, points }, ranks };
}

async function loadLayer(list, color, editionId) {
    const { data } = await api.get(`/map/rankings/${list.id}/points`, { params: { edition_id: editionId } });
    const name = `${list.name} ${data.edition}`;
    return toLayer(name, color, pointsFromCompact(data.fields, data.points), () => name);
}

// Every state's list for one edition, as one layer.
async function loadAllStatesLayer(editionLabel, color) {
    const { data } = await api.get('/map/rankings/states/points', { params: { edition: editionLabel } });
    return toLayer(
        `Best in State ${data.edition}`,
        color,
        pointsFromCompact(data.fields, data.points),
        p => `${p.list} ${data.edition}`,
    );
}

// Private clubs hidden; a course with no access label stays (mostly resorts).
function publicOnlyView(layer) {
    const points = layer.group.points.filter(p => p.access !== 'private');
    const keep = new Set(points.map(p => p.id));
    return {
        group: { ...layer.group, points },
        ranks: Object.fromEntries(Object.entries(layer.ranks).filter(([id]) => keep.has(Number(id)))),
    };
}

function AllUsersMap() {
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const [userGroups, setUserGroups] = useState([]);
    const [lists, setLists] = useState([]);
    // Per regular list: whether its layer is on and which edition. The first list starts on.
    const [layers, setLayers] = useState({});
    // The Best in State layer: off, all states or one list, an edition label, and a private-club filter.
    const [stateLayer, setStateLayer] = useState({ on: false, state: ALL_STATES, edition: null, publicOnly: false });
    // layer key -> { group, ranks } once loaded.
    const [loaded, setLoaded] = useState({});
    const requested = useRef(new Set());
    // Bumped on every refresh so the layer effect runs again even when the
    // rankings call failed and `lists`/`layers` therefore did not change.
    const [refreshCount, setRefreshCount] = useState(0);
    // Bumped on every (re)load so a layer response from before a refresh is ignored.
    const generation = useRef(0);
    // Keys of layers whose last fetch failed, so the bar can say so.
    const [failed, setFailed] = useState(() => new Set());

    const rankingLists = useMemo(() => lists.filter(l => !isStateList(l)), [lists]);
    const stateLists = useMemo(
        () => lists.filter(isStateList).sort((a, b) => stateName(a).localeCompare(stateName(b))),
        [lists],
    );
    // Editions are the same for every state; newest first as the API returns them.
    const stateEditions = useMemo(() => {
        const labels = [];
        stateLists.forEach(l => l.editions.forEach(e => { if (!labels.includes(e.label)) labels.push(e.label); }));
        return labels;
    }, [stateLists]);
    const stateEdition = stateEditions.includes(stateLayer.edition) ? stateLayer.edition : stateEditions[0];
    const selectedState = stateLists.find(l => String(l.id) === String(stateLayer.state)) ?? null;

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
                setLayers(prev => Object.fromEntries(usable.filter(l => !isStateList(l)).map((l, i) => {
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

    // The layers to show, in order: one per switched-on list, then Best in State.
    const defs = useMemo(() => {
        const out = [];
        rankingLists.forEach((list, i) => {
            const layer = layers[list.id];
            if (!layer?.on) return;
            out.push({
                key: layerKey(list.id, layer.editionId),
                load: () => loadLayer(list, RANKING_COLORS[i % RANKING_COLORS.length], layer.editionId),
            });
        });
        if (stateLayer.on && stateEdition) {
            if (selectedState) {
                const editionId = selectedState.editions.find(e => e.label === stateEdition)?.id;
                out.push({
                    key: layerKey(selectedState.id, editionId),
                    load: () => (editionId == null
                        ? Promise.reject(new Error('edition not published for this state'))
                        : loadLayer(selectedState, STATE_RANKING_COLOR, editionId)),
                    state: true,
                });
            } else {
                out.push({
                    key: `states:${stateEdition}`,
                    load: () => loadAllStatesLayer(stateEdition, STATE_RANKING_COLOR),
                    state: true,
                });
            }
        }
        return out;
    }, [rankingLists, layers, stateLayer.on, stateEdition, selectedState]);

    // Fetch each wanted layer once; a failure just leaves that layer out.
    useEffect(() => {
        defs.forEach(def => {
            if (requested.current.has(def.key)) return;
            requested.current.add(def.key);
            const gen = generation.current;
            setFailed(prev => { if (!prev.has(def.key)) return prev; const next = new Set(prev); next.delete(def.key); return next; });
            def.load()
                .then(result => { if (gen === generation.current) setLoaded(prev => ({ ...prev, [def.key]: result })); })
                .catch(() => {
                    if (gen !== generation.current) return;
                    requested.current.delete(def.key);  // toggling the layer off and on retries
                    setFailed(prev => new Set(prev).add(def.key));
                });
        });
    }, [defs, refreshCount]);

    const stateDef = defs.find(d => d.state);
    const stateResult = stateDef ? loaded[stateDef.key] : undefined;
    // Memoized on its own so toggling another layer does not re-fit the map to the state.
    const stateView = useMemo(
        () => (stateResult && stateLayer.publicOnly ? publicOnlyView(stateResult) : stateResult),
        [stateResult, stateLayer.publicOnly],
    );

    const { groups, ranks } = useMemo(() => {
        const rankingGroups = [];
        const ranks = {};
        defs.forEach(def => {
            const result = def.state ? stateView : loaded[def.key];
            if (!result) return;
            rankingGroups.push(result.group);
            Object.entries(result.ranks).forEach(([id, r]) => { (ranks[id] ??= []).push(r); });
        });
        return { groups: [...userGroups, ...rankingGroups], ranks };
    }, [defs, loaded, stateView, userGroups]);

    // Zoom to a single state when one is picked; all states or other layers leave the view alone.
    const focusPoints = selectedState && stateView ? stateView.group.points : null;

    const setLayer = (listId, patch) => setLayers(prev => ({ ...prev, [listId]: { ...prev[listId], ...patch } }));
    const patchState = patch => setStateLayer(prev => ({ ...prev, ...patch }));

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
                    {rankingLists.map(list => (
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
                    {stateLists.length > 0 && (
                        <div className="map-rankings-layer">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={stateLayer.on}
                                    onChange={e => patchState({ on: e.target.checked })}
                                />{' '}
                                Best in State
                            </label>
                            <select
                                aria-label="Best in State state"
                                value={selectedState ? selectedState.id : ALL_STATES}
                                onChange={e => patchState({ state: e.target.value })}
                            >
                                <option value={ALL_STATES}>All states</option>
                                {stateLists.map(l => <option key={l.id} value={l.id}>{stateName(l)}</option>)}
                            </select>
                            <select
                                aria-label="Best in State edition"
                                value={stateEdition ?? ''}
                                onChange={e => patchState({ edition: e.target.value })}
                            >
                                {stateEditions.map(label => <option key={label} value={label}>{label}</option>)}
                            </select>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={stateLayer.publicOnly}
                                    onChange={e => patchState({ publicOnly: e.target.checked })}
                                />{' '}
                                Public only
                            </label>
                            {stateLayer.on && stateDef && failed.has(stateDef.key) && (
                                <span role="alert">⚠ couldn't load</span>
                            )}
                        </div>
                    )}
                </div>
            )}

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}
            {status === 'loaded' && <CourseMap groups={groups} showLegend ranks={ranks} focusPoints={focusPoints} />}
        </div>
    );
}

export default AllUsersMap;
