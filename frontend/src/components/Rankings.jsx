import React, { useEffect, useState } from 'react';
import api from '../services/api';

function Rankings() {
    const [lists, setLists] = useState([]);
    const [listId, setListId] = useState(null);
    const [editionId, setEditionId] = useState(null);
    const [edition, setEdition] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        api.get('/rankings')
            .then(res => {
                setLists(res.data);
                const first = res.data[0];
                if (first) {
                    setListId(first.id);
                    setEditionId(first.editions[0]?.id ?? null);
                }
            })
            .catch(() => setError('Failed to load rankings. Please try again.'))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (editionId == null) return;
        let cancelled = false;
        setEdition(null);
        api.get(`/rankings/editions/${editionId}`)
            .then(res => { if (!cancelled) setEdition(res.data); })
            .catch(() => { if (!cancelled) setError('Failed to load this edition. Please try again.'); });
        return () => { cancelled = true; };
    }, [editionId]);

    const list = lists.find(l => l.id === listId);

    const changeList = (id) => {
        const next = lists.find(l => l.id === id);
        setError('');
        setListId(id);
        setEditionId(next?.editions[0]?.id ?? null);
    };

    if (loading) return <p className="loading-text">Loading rankings…</p>;
    if (!list) {
        return (
            <div className="course-list">
                {error
                    ? <div className="alert-danger" role="alert">{error}</div>
                    : <div className="empty-state">No rankings yet.</div>}
            </div>
        );
    }

    const entries = edition?.entries ?? [];
    const played = entries.filter(e => e.played).length;

    return (
        <div className="course-list">
            {error && <div className="alert-danger" role="alert">{error}</div>}
            <div className="page-header">
                <div>
                    <div className="page-title">Rankings</div>
                    <div className="page-subtitle">{list.publisher}: {list.name}</div>
                </div>
                <div className="page-header-actions">
                    {lists.length > 1 && (
                        <select aria-label="Ranking list" value={listId} onChange={e => changeList(Number(e.target.value))}>
                            {lists.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                        </select>
                    )}
                    <select
                        aria-label="Edition"
                        value={editionId ?? ''}
                        onChange={e => { setError(''); setEditionId(Number(e.target.value)); }}
                    >
                        {list.editions.map(ed => <option key={ed.id} value={ed.id}>{ed.label}</option>)}
                    </select>
                </div>
            </div>

            {edition && (
                <div className="stat-row">
                    <div className="stat-chip">
                        <div className="stat-value">{played} / {entries.length}</div>
                        <div className="stat-label">You've Played</div>
                    </div>
                </div>
            )}

            <div className="table-card">
                <div style={{ overflowX: 'auto' }}>
                    <table className="fairway-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Previous</th>
                                <th>Course</th>
                                <th>City</th>
                                <th>State</th>
                                <th>Played</th>
                            </tr>
                        </thead>
                        <tbody>
                            {entries.map(e => (
                                <tr key={e.rank}>
                                    <td>{e.rank}</td>
                                    <td>{e.prior_rank ?? '—'}</td>
                                    <td title={e.published_name !== e.name ? e.published_name : undefined}>{e.name}</td>
                                    <td>{e.city}</td>
                                    <td>{e.state}</td>
                                    <td>{e.played ? '✓' : ''}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default Rankings;
