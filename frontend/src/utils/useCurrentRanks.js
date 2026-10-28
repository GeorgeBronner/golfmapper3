import { useEffect, useState } from 'react';
import api from '../services/api';

// One load shared by every map mount; a failed or empty load is not cached.
let cached = null;

async function loadRanks() {
    const { data: lists } = await api.get('/rankings');
    const list = Array.isArray(lists) ? lists[0] : null;
    const edition = list?.editions?.[0];
    if (!edition) return null;
    const { data } = await api.get(`/rankings/editions/${edition.id}`);
    if (!Array.isArray(data?.entries)) return null;
    const label = `${list.publisher} ${edition.label}`;
    return Object.fromEntries(data.entries.map(e => [e.course_id, { rank: e.rank, label }]));
}

// Rank of each course in the newest edition of the first ranking list, as
// { [courseId]: { rank, label } }, for map popups. Ranks are decoration, so a
// failed load leaves the map working without them.
export default function useCurrentRanks() {
    const [ranks, setRanks] = useState(null);

    useEffect(() => {
        let cancelled = false;
        cached ??= loadRanks().catch(() => null);  // keep the map usable without ranks
        cached.then(r => {
            if (!r) cached = null;
            else if (!cancelled) setRanks(r);
        });
        return () => { cancelled = true; };
    }, []);

    return ranks;
}
