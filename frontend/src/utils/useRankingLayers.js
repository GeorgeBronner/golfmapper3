import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from '../components/AuthProvider';
import { pointsFromCompact, RANKING_COLORS, STATE_RANKING_COLOR } from './mapPoints';

// Each state's Best in State list is its own ranking list with this scope prefix.
// They get one "Best in State" control instead of a checkbox apiece.
const STATE_SCOPE_PREFIX = 'us-state-';
export const isStateList = list => list.scope?.startsWith(STATE_SCOPE_PREFIX);
export const stateName = list => list.name.replace(/^Best Courses in /, '');
export const ALL_STATES = 'ALL';

export const layerKey = (listId, editionId) => `${listId}:${editionId}`;

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

/**
 * The ranking-list layers shared by the maps: which lists and editions are
 * switched on, their loaded points, and the state of the Best in State control.
 *
 * Returns { ui, groups, ranks, focusPoints, refresh }:
 *  - ui: everything RankingLayersBar needs to draw and drive the controls;
 *  - groups: one map group per switched-on layer, in display order;
 *  - ranks: { [courseId]: [{ rank, label, tied }] } for the popups;
 *  - focusPoints: the points to zoom to when a single state is picked, else null;
 *  - refresh(): reload the lists and every layer.
 *
 * The ranking lists are extras: a failed load leaves the map working without them.
 * firstOn switches the first list on by default.
 */
export default function useRankingLayers({ firstOn = true } = {}) {
    const { token } = useAuth();
    const activeCallRef = useRef(null);
    const [lists, setLists] = useState([]);
    // Per regular list: whether its layer is on and which edition.
    const [layers, setLayers] = useState({});
    // The Best in State layer: off, all states or one list, an edition label, and a private-club filter.
    const [stateLayer, setStateLayer] = useState({ on: false, state: ALL_STATES, edition: null, publicOnly: false });
    // Off by default: every list shows its newest edition and the year pickers are hidden.
    const [showOld, setShowOld] = useState(false);
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
    const stateEdition = showOld && stateEditions.includes(stateLayer.edition) ? stateLayer.edition : stateEditions[0];
    const selectedState = stateLists.find(l => String(l.id) === String(stateLayer.state)) ?? null;
    const stateEditionMissing = !!selectedState && !!stateEdition
        && !selectedState.editions.some(e => e.label === stateEdition);

    const refresh = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        let fetched = null;
        try {
            const r = await api.get('/rankings');
            fetched = Array.isArray(r.data) ? r.data : null;
        } catch {
            fetched = null;
        }
        if (activeCallRef.current !== callId) return;
        // If the rankings call failed, keep the lists and choices we already have.
        if (fetched) {
            const usable = fetched.filter(l => l.editions?.length);
            setLists(usable);
            setLayers(prev => Object.fromEntries(usable.filter(l => !isStateList(l)).map((l, i) => {
                const old = prev[l.id];
                const stillThere = old && l.editions.some(e => e.id === old.editionId);
                return [l.id, stillThere ? old : { on: old ? old.on : firstOn && i === 0, editionId: l.editions[0].id }];
            })));
        }
        generation.current += 1;
        // A refresh reloads the layers too. The old layers stay drawn until the new data
        // replaces them, so the map does not blank out and flicker.
        requested.current = new Set();
        setFailed(new Set());
        setRefreshCount(n => n + 1);
    }, [firstOn]);

    useEffect(() => { refresh(); }, [token, refresh]);

    // The layers to show, in order: one per switched-on list, then Best in State.
    const defs = useMemo(() => {
        const out = [];
        rankingLists.forEach((list, i) => {
            const layer = layers[list.id];
            if (!layer?.on) return;
            const editionId = showOld ? layer.editionId : list.editions[0].id;
            out.push({
                key: layerKey(list.id, editionId),
                load: () => loadLayer(list, RANKING_COLORS[i % RANKING_COLORS.length], editionId),
            });
        });
        if (stateLayer.on && stateEdition) {
            if (selectedState) {
                const editionId = selectedState.editions.find(e => e.label === stateEdition)?.id;
                // A state without this edition has nothing to load; the bar says so.
                if (editionId != null) {
                    out.push({
                        key: layerKey(selectedState.id, editionId),
                        load: () => loadLayer(selectedState, STATE_RANKING_COLOR, editionId),
                        state: true,
                    });
                }
            } else {
                out.push({
                    key: `states:${stateEdition}`,
                    load: () => loadAllStatesLayer(stateEdition, STATE_RANKING_COLOR),
                    state: true,
                });
            }
        }
        return out;
    }, [rankingLists, layers, showOld, stateLayer.on, stateEdition, selectedState]);

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
        const groups = [];
        const ranks = {};
        defs.forEach(def => {
            const result = def.state ? stateView : loaded[def.key];
            if (!result) return;
            groups.push(result.group);
            Object.entries(result.ranks).forEach(([id, r]) => { (ranks[id] ??= []).push(r); });
        });
        return { groups, ranks };
    }, [defs, loaded, stateView]);

    // Zoom to a single state when one is picked; all states or other layers leave the view alone.
    const focusPoints = selectedState && stateView ? stateView.group.points : null;

    const setLayer = useCallback(
        (listId, patch) => setLayers(prev => ({ ...prev, [listId]: { ...prev[listId], ...patch } })),
        [],
    );
    const patchState = useCallback(patch => setStateLayer(prev => ({ ...prev, ...patch })), []);

    // Old lists only matter when some list has more than one edition.
    const hasOldLists = rankingLists.some(l => l.editions.length > 1) || stateEditions.length > 1;

    const ui = {
        showOld,
        setShowOld,
        hasOldLists,
        rankingLists,
        layers,
        setLayer,
        stateLists,
        stateLayer,
        patchState,
        selectedState,
        stateEditions,
        stateEdition,
        stateEditionMissing,
        failed,
        stateKey: stateDef?.key,
    };
    return { ui, groups, ranks, focusPoints, refresh };
}
