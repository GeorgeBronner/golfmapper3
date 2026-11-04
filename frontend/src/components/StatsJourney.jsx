import React from 'react';
import { buildJourney } from '../utils/statsData';
import { StatCard, Ring, HBar, LineChart } from './StatsParts';
import { shortName } from './StatsOverview';

export default function StatsJourney({ stats, progress, listName }) {
    const t = stats.list;
    const journey = buildJourney(progress, stats.years);
    const maxBig = journey.biggest[0]?.courses.length || 1;
    const name = (c) => shortName(c.name);

    return (
        <div className="stats-grid stats-wide">
            <div className="stats-stack">
                <StatCard title={`${listName} progress over time`} aside="cumulative courses played that have been on the list">
                    <LineChart points={journey.cumulative} />
                </StatCard>
                <StatCard title="Year by year" aside={`${listName} courses played${journey.undated ? ` · ${journey.undated} with no year set` : ''}`}>
                    {journey.timeline.length === 0 && <div className="stats-muted">No {listName} courses played yet.</div>}
                    <div className="stats-tl">
                        {journey.timeline.map(y => (
                            <div key={y.year} className={`stats-tl-y ${y.courses.length >= 5 ? 'hl' : ''}`}>
                                <h4>{y.year}<small>{y.courses.length} {listName} {y.courses.length === 1 ? 'course' : 'courses'} · {y.playedThatYear} played that year</small></h4>
                                {y.courses.map(c => (
                                    <span key={c.course_id} className="stats-pill" title={c.name}>
                                        {c.current_rank ? <b>#{c.current_rank}</b> : <span className="stats-sub">off list</span>} {name(c)}
                                    </span>
                                ))}
                            </div>
                        ))}
                    </div>
                </StatCard>
            </div>
            <div className="stats-stack">
                <StatCard title={`${listName} ${t.label}`}>
                    <div className="stats-row">
                        <Ring pct={t.size ? t.played / t.size : 0} size={110} stroke={11}>
                            <b>{t.played}</b><small>of {t.size}</small>
                        </Ring>
                        <div className="stats-best">
                            <div>{t.everPlayed} of {t.everListed} courses ever on this list played</div>
                            {t.highest.slice(0, 2).map(c => (
                                <div key={c.course_id} className="stats-best-row" title={c.name}><b className="stats-gold">#{c.current_rank}</b><span>{name(c)}</span></div>
                            ))}
                        </div>
                    </div>
                </StatCard>
                {journey.biggest.length > 0 && (
                    <StatCard title="Biggest years" aside="most list courses played">
                        {journey.biggest.map(y => <HBar key={y.year} label={y.year} value={y.courses.length} max={maxBig} />)}
                    </StatCard>
                )}
                {journey.first && (
                    <StatCard title="First and latest">
                        <div className="stats-li"><span className="stats-badge">FIRST</span><span className="stats-li-name">{journey.first.year} · {name(journey.first.course)}</span></div>
                        <div className="stats-li"><span className="stats-badge g">LATEST</span><span className="stats-li-name">{journey.latest.year} · {name(journey.latest.course)}</span></div>
                    </StatCard>
                )}
            </div>
        </div>
    );
}
