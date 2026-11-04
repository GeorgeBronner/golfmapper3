import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../services/api';
import { buildStats, isStateList, isWorldList, listShortName } from '../utils/statsData';
import { Tabs } from './StatsParts';
import StatsOverview from './StatsOverview';
import StatsJourney from './StatsJourney';
import StatsBestInState from './StatsBestInState';
import './Stats.css';

function Stats() {
    const [courses, setCourses] = useState(null);
    const [lists, setLists] = useState(null);          // the ranking lists that have a Top N (not Best in State)
    const [listId, setListId] = useState(null);
    const [progress, setProgress] = useState({});      // list id -> /rankings/lists/{id}/progress
    const [editions, setEditions] = useState({});      // list id -> newest edition's entries
    const [bis, setBis] = useState(null);              // /rankings/states/progress
    const [bisRequested, setBisRequested] = useState(false);
    const [error, setError] = useState('');
    const [tab, setTab] = useState('overview');

    useEffect(() => {
        let cancelled = false;
        api.get('/user_courses/readall_ids_w_year', { params: { include_unmapped: true } })
            .then(res => { if (!cancelled) setCourses(res.data); })
            .catch(() => { if (!cancelled) setError('Failed to load your stats. Please try again.'); });
        // The ranking parts are decoration: without rankings the rest still works.
        api.get('/rankings')
            .then(({ data }) => {
                if (cancelled || !Array.isArray(data)) return;
                const top = data.filter(l => !isStateList(l));
                setLists(top);
                // Open on the US Public list (the 100-course list) when there is one.
                setListId((top.find(l => l.scope === 'us-public') ?? top.find(l => l.size === 100) ?? top[0])?.id ?? null);
            })
            .catch(() => { /* leave lists null */ });
        return () => { cancelled = true; };
    }, []);

    // Load the chosen list's progress and its current edition, once per list. A ref (not the
    // `progress` state) records what was requested, so storing the result does not cancel the
    // follow-up request for the edition's entries.
    const requested = useRef(new Set());
    const mounted = useRef(true);
    useEffect(() => {
        mounted.current = true; // set again on mount: StrictMode runs the cleanup once in development
        return () => { mounted.current = false; };
    }, []);
    useEffect(() => {
        if (listId == null || requested.current.has(listId)) return;
        requested.current.add(listId);
        api.get(`/rankings/lists/${listId}/progress`)
            .then(async ({ data }) => {
                if (!mounted.current) return;
                setProgress(prev => ({ ...prev, [listId]: data }));
                if (data.current?.id != null) {
                    const res = await api.get(`/rankings/editions/${data.current.id}`);
                    if (mounted.current) setEditions(prev => ({ ...prev, [listId]: res.data.entries }));
                }
            })
            .catch(() => { requested.current.delete(listId); });
    }, [listId]);

    const needBis = useCallback(() => setBisRequested(true), []);
    useEffect(() => {
        if (tab === 'bis') setBisRequested(true);
    }, [tab]);
    useEffect(() => {
        if (!bisRequested || bis) return undefined;
        let cancelled = false;
        api.get('/rankings/states/progress')
            .then(res => { if (!cancelled) setBis(res.data); })
            .catch(() => { if (!cancelled) setBis({ states: {} }); });
        return () => { cancelled = true; };
    }, [bisRequested, bis]);

    const list = lists?.find(l => l.id === listId) ?? null;
    const listProgress = listId != null ? progress[listId] ?? null : null;
    const stats = useMemo(() => (courses ? buildStats(courses, listProgress) : null), [courses, listProgress]);

    if (error) return <div className="course-list"><div className="alert-danger" role="alert">{error}</div></div>;
    if (!stats) return <p className="loading-text">Loading stats…</p>;
    if (stats.total === 0) {
        return (
            <div className="course-list">
                <div className="page-header"><div><div className="page-title">My Stats</div></div></div>
                <div className="empty-state">Add a course to start seeing your stats.</div>
            </div>
        );
    }

    const hasRankings = !!(lists && lists.length);
    const listName = list ? listShortName(list) : '';
    const showPicker = hasRankings && tab !== 'bis';
    // The Journey tab needs the list's progress; fall back to Overview if it never loads.
    const activeTab = hasRankings ? tab : 'overview';

    return (
        <div className="stats-page">
            <div className="page-header">
                <div>
                    <div className="page-title">My Stats</div>
                    <div className="page-subtitle">Where you've played and how you're tracking on Golf Digest's lists</div>
                </div>
                {showPicker && (
                    <div className="stats-picker" role="group" aria-label="Ranking list">
                        {lists.map(l => (
                            <button key={l.id} type="button" className={l.id === listId ? 'on' : ''} aria-pressed={l.id === listId} onClick={() => setListId(l.id)}>{listShortName(l)}</button>
                        ))}
                    </div>
                )}
            </div>

            {hasRankings && (
                <Tabs value={activeTab} onChange={setTab} options={[['overview', 'Overview'], ['journey', 'Journey'], ['bis', 'Best in State']]} />
            )}

            {activeTab === 'overview' && (
                <StatsOverview
                    stats={stats}
                    courses={courses}
                    list={list}
                    listName={listName}
                    entries={listId != null ? editions[listId] : undefined}
                    world={isWorldList(list)}
                    bis={bis && Object.keys(bis.states).length ? bis : null}
                    onNeedBis={needBis}
                />
            )}
            {activeTab === 'journey' && (stats.list
                ? <StatsJourney stats={stats} progress={listProgress} listName={listName} />
                : <p className="loading-text">Loading…</p>)}
            {activeTab === 'bis' && <StatsBestInState stats={stats} data={bis} />}
        </div>
    );
}

export default Stats;
