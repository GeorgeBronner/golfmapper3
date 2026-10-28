import { useEffect, useState } from 'react';
import api from '../services/api';

// Rank of each course in the newest edition of the first ranking list, as
// { [courseId]: { rank, label } }, for map popups. Ranks are decoration, so a
// failed load leaves the map working without them.
export default function useCurrentRanks() {
    const [ranks, setRanks] = useState(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const { data: lists } = await api.get('/rankings');
                const list = Array.isArray(lists) ? lists[0] : null;
                const edition = list?.editions?.[0];
                if (!edition) return;
                const { data } = await api.get(`/rankings/editions/${edition.id}`);
                if (cancelled || !Array.isArray(data?.entries)) return;
                const label = `${list.publisher} ${edition.label}`;
                setRanks(Object.fromEntries(data.entries.map(e => [e.course_id, { rank: e.rank, label }])));
            } catch {
                // keep the map usable without ranks
            }
        })();
        return () => { cancelled = true; };
    }, []);

    return ranks;
}
