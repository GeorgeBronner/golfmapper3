import React, { useEffect, useMemo, useState } from 'react';
import api from '../services/api';
import { buildStats } from '../utils/statsData';
import { STATE_CODES } from '../utils/usStates';
import { StatCard, StatTile, Ring, HBar, StateMap, YearColumns } from './StatsParts';
import './Stats.css';

// Shorten "Club - Course" display names to the course part for tight rows.
const shortName = (name) => {
    const i = name.indexOf(' - ');
    return i >= 0 ? name.slice(i + 3).trim() : name;
};

function Stats() {
    const [courses, setCourses] = useState(null);
    const [progress, setProgress] = useState(null);
    const [error, setError] = useState('');
    const [layer, setLayer] = useState('courses');

    useEffect(() => {
        let cancelled = false;
        api.get('/user_courses/readall_ids_w_year', { params: { include_unmapped: true } })
            .then(res => { if (!cancelled) setCourses(res.data); })
            .catch(() => { if (!cancelled) setError('Failed to load your stats. Please try again.'); });
        // The Top 100 parts are decoration: without rankings the rest still works.
        api.get('/rankings')
            .then(({ data: lists }) => {
                // The copy below says "Top 100", so prefer the 100-course list over whatever comes first.
                const list = Array.isArray(lists) ? (lists.find(l => l.size === 100) ?? lists[0]) : null;
                return list ? api.get(`/rankings/lists/${list.id}/progress`) : null;
            })
            .then(res => { if (res && !cancelled) setProgress(res.data); })
            .catch(() => { /* leave progress null */ });
        return () => { cancelled = true; };
    }, []);

    const stats = useMemo(() => (courses ? buildStats(courses, progress) : null), [courses, progress]);

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

    const t = stats.top100;
    const maxStateRanked = t ? Math.max(...t.topStates.map(s => s.ranked), 1) : 1;

    return (
        <div className="stats-page">
            <div className="page-header">
                <div>
                    <div className="page-title">My Stats</div>
                    <div className="page-subtitle">Where you've played and how you're tracking on the Top 100</div>
                </div>
            </div>

            <div className="stats-grid stats-g4">
                <StatTile value={stats.total} label="Courses played" sub={`at ${stats.clubs} ${stats.clubs === 1 ? 'club' : 'clubs'}`} />
                <StatTile
                    value={`${stats.states}/${STATE_CODES.length}`}
                    label="States"
                    sub={`${stats.countries} ${stats.countries === 1 ? 'country' : 'countries'}`}
                />
                {t && (
                    <>
                        <StatTile
                            value={<>{t.played}<span className="stats-of">/{t.size}</span></>}
                            label="On today's Top 100"
                            sub={`${t.label} edition`}
                        />
                        <StatTile value={t.everPlayed} label="Ranked at some point" sub={`of ${t.everListed} courses ever listed`} />
                    </>
                )}
            </div>

            <div className="stats-grid stats-wide">
                <StatCard
                    title="Where you've played"
                    aside={t && (
                        <span className="stats-seg" role="group" aria-label="Map layer">
                            <button type="button" className={layer === 'courses' ? 'on' : ''} onClick={() => setLayer('courses')}>Courses</button>
                            <button type="button" className={layer === 'top100' ? 'on' : ''} onClick={() => setLayer('top100')}>Top 100</button>
                        </span>
                    )}
                >
                    <StateMap layer={layer} byState={stats.byState} top100={t} />
                    <div className="stats-legend">
                        {layer === 'courses'
                            ? <><span>Darker = more courses</span>{t && <span><b className="stats-gold">★</b> = Top 100 courses played</span>}</>
                            : <span>Gold = Top 100 courses played / ranked in state · outlined = none yet</span>}
                    </div>
                </StatCard>

                {t && (
                    <div className="stats-stack">
                        <StatCard title="Top 100 progress">
                            <div className="stats-row">
                                <Ring pct={t.size ? t.played / t.size : 0}>
                                    <b>{t.played}</b><small>of {t.size}</small>
                                </Ring>
                                <div className="stats-best">
                                    <div className="stats-muted">HIGHEST RANKED PLAYED</div>
                                    {t.highest.length === 0 && <div className="stats-muted">None yet</div>}
                                    {t.highest.map(c => (
                                        <div key={c.course_id} className="stats-best-row" title={c.name}>
                                            <b className="stats-gold">#{c.current_rank}</b>
                                            <span>{shortName(c.name)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </StatCard>
                        <StatCard title="Top 100 courses by state" aside="played / ranked">
                            {t.topStates.map(s => (
                                <HBar key={s.code} label={s.code} value={s.played} max={maxStateRanked} right={`${s.played}/${s.ranked}`} />
                            ))}
                        </StatCard>
                    </div>
                )}
            </div>

            {stats.years.length > 0 && (
                <StatCard title="Courses per year" aside={stats.undated ? `${stats.undated} with no year set` : undefined}>
                    <div className="stats-cols-wrap"><YearColumns rows={stats.years} /></div>
                    {t && (
                        <div className="stats-legend">
                            <span><i className="stats-dot stats-dot-gold" />Top 100 courses (any edition)</span>
                            <span><i className="stats-dot" />Everything else</span>
                        </div>
                    )}
                </StatCard>
            )}
        </div>
    );
}

export default Stats;
