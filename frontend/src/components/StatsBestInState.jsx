import React, { useMemo, useState } from 'react';
import { STATE_NAMES } from '../utils/usStates';
import { RANK_TIERS, buildBestInState, defaultBestInStateCode, sortBestInState, tierCell } from '../utils/statsData';
import { StatCard, StatTile, HBar, Seg, StateMap } from './StatsParts';
import { CourseRow, shortName } from './StatsOverview';

const CHARTS = [['bars', 'Bars'], ['pips', 'Course pips'], ['size', 'Size & fill'], ['scatter', 'Scatter'], ['tiers', 'Rank tiers']];
const CHART_INFO = {
    bars: 'Played over ranked, per state.',
    pips: 'One square per ranked course, in rank order, left to right. Gold = played, so you can see which ranks you have, not just how many.',
    size: 'Bar length is how many courses the state ranks; the filled part is what you have played. Private courses are hatched.',
    scatter: 'Each dot is a state. Right = more ranked courses, up = more complete. Bottom right = big states you have barely touched.',
    tiers: 'How you do at each level of the ranking. Shade = share played, so you can see whether you play the best courses or the rest.',
};
const SORTS = [['pct', 'Most complete'], ['left', 'Most left'], ['az', 'A–Z']];

function Legend({ publicOnly, hatched = false }) {
    return (
        <div className="stats-legend">
            <span><i className="stats-dot stats-dot-gold" />Played</span>
            <span><i className="stats-dot stats-dot-grey" />Public, not yet</span>
            {!publicOnly && <span><i className={`stats-dot ${hatched ? 'stats-hatch' : 'stats-dot-outline'}`} />Private, not yet</span>}
        </div>
    );
}

function BarsChart({ rows }) {
    return (
        <div className="stats-two-col">
            {rows.map(r => <HBar key={r.code} label={r.code} value={r.p} max={r.t} right={`${r.p}/${r.t}`} green={r.p === r.t} />)}
        </div>
    );
}

function PipsChart({ rows, publicOnly }) {
    return (
        <>
            <div className="stats-two-col">
                {rows.map(r => (
                    <div key={r.code} className="stats-pr">
                        <span className="stats-pr-l">{r.name}</span>
                        <span className="stats-pips">
                            {r.entries.map(e => (
                                <i
                                    key={e.course_id}
                                    className={`stats-pip ${e.played ? 'p' : e.access === 'private' ? 'x' : ''}`}
                                    title={`#${e.rank} ${e.name}${e.played ? ' (played)' : ''}`}
                                />
                            ))}
                        </span>
                        <span className="stats-pr-v">{r.p}/{r.t}</span>
                    </div>
                ))}
            </div>
            <Legend publicOnly={publicOnly} />
        </>
    );
}

function SizeChart({ rows, publicOnly }) {
    const max = Math.max(...rows.map(r => r.t), 1);
    return (
        <>
            {rows.map(r => (
                <div key={r.code} className="stats-pr">
                    <span className="stats-pr-l">{r.name}</span>
                    <span className="stats-pr-bar">
                        <span className="stats-seg3" style={{ width: `${(r.t / max) * 100}%` }}>
                            <span style={{ flex: r.p, background: 'var(--stats-gold)' }} />
                            <span style={{ flex: r.leftPub, background: 'var(--surface-3, #e7ebe9)' }} />
                            {!publicOnly && <span className="stats-hatch" style={{ flex: r.leftPriv }} />}
                        </span>
                    </span>
                    <span className="stats-pr-v">{r.p}/{r.t}</span>
                </div>
            ))}
            <Legend publicOnly={publicOnly} hatched />
        </>
    );
}

function ScatterChart({ rows }) {
    const W = 640, H = 320, P = 34;
    const maxT = Math.max(...rows.map(r => r.t), 1) + 4;
    const maxF = Math.min(1, Math.ceil(Math.max(...rows.map(r => r.p / r.t), 0) * 10 + 1) / 10);
    const x = (v) => P + (v / maxT) * (W - P * 1.6);
    const y = (f) => H - P - (f / maxF) * (H - P * 1.6);
    const qx = x(maxT * 0.5);
    const qy = y(maxF * 0.3);
    return (
        <>
            <svg className="stats-scatter" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Best in State progress by state size">
                {[0, 0.25, 0.5, 0.75, 1].map(k => (
                    <g key={k}>
                        <line x1={P} x2={W - 8} y1={y(maxF * k)} y2={y(maxF * k)} stroke="var(--border)" />
                        <text x="2" y={y(maxF * k) + 3}>{Math.round(maxF * k * 100)}%</text>
                    </g>
                ))}
                <text x={W / 2 - 60} y={H - 6}>ranked courses in the state →</text>
                <rect x={qx} y={qy} width={W - 8 - qx} height={H - P - qy} fill="var(--stats-gold)" opacity=".08" />
                <text x={W - 150} y={H - P - 6} className="stats-scatter-q">big states, barely touched</text>
                {rows.slice().sort((a, b) => b.t - a.t).map(r => {
                    const f = r.p / r.t;
                    const rad = 4 + Math.sqrt(r.t - r.p) * 0.9;
                    return (
                        <g key={r.code}>
                            <circle cx={x(r.t)} cy={y(f)} r={rad} fill={f >= 1 ? 'var(--primary)' : 'var(--stats-gold)'} opacity=".6" stroke="#fff">
                                <title>{`${r.name}: ${r.p}/${r.t}`}</title>
                            </circle>
                            {(r.t >= 20 || f >= 0.4) && <text x={x(r.t) + rad + 2} y={y(f) + 3} className="stats-scatter-l">{r.code}</text>}
                        </g>
                    );
                })}
            </svg>
            <div className="stats-legend"><span>Dot size = courses left to play · green = complete · small states are unlabeled (hover for details)</span></div>
        </>
    );
}

function TiersChart({ rows }) {
    const cells = rows.map(r => ({ r, cells: RANK_TIERS.map(t => tierCell(r, t)) }));
    const topScore = (c) => c.cells[0].p + c.cells[1].p;
    cells.sort((a, b) => topScore(b) - topScore(a) || b.r.p - a.r.p || a.r.name.localeCompare(b.r.name));
    return (
        <div className="stats-tiers">
            <div className="stats-tier"><span />{RANK_TIERS.map(t => <span key={t[2]} className="h">{t[2]}</span>)}</div>
            {cells.map(({ r, cells: row }) => (
                <div key={r.code} className="stats-tier">
                    <span className="n">{r.name}</span>
                    {row.map((c, i) => (
                        c.t
                            ? <span key={i} className="c" style={c.p ? { background: `color-mix(in srgb, var(--stats-gold) ${Math.round(25 + (c.p / c.t) * 75)}%, white)`, color: '#5b3a00', fontWeight: 600 } : undefined}>{c.p}/{c.t}</span>
                            : <span key={i} className="c dim">–</span>
                    ))}
                </div>
            ))}
        </div>
    );
}

export default function StatsBestInState({ stats, data }) {
    const [publicOnly, setPublicOnly] = useState(false);
    const [chart, setChart] = useState('bars');
    const [sort, setSort] = useState('pct');
    const [picked, setPicked] = useState(null);

    const all = useMemo(() => (data ? buildBestInState(data.states, false) : null), [data]);
    const view = useMemo(() => (data ? buildBestInState(data.states, publicOnly) : null), [data, publicOnly]);
    if (!data) return <p className="loading-text">Loading Best in State…</p>;
    if (!view.rows.length) return <div className="empty-state">No Best in State rankings yet.</div>;

    const selected = picked ?? defaultBestInStateCode(all.rows);
    const current = view.byCode[selected];
    const label = Object.values(data.states)[0]?.label;
    const rows = sortBestInState(view.rows, sort);
    const sortable = chart !== 'scatter' && chart !== 'tiers';

    return (
        <>
            <div className="stats-filter">
                <span className="stats-muted">Showing:</span>
                <Seg label="Course access" value={publicOnly ? 'pub' : 'all'} onChange={v => setPublicOnly(v === 'pub')} options={[['all', 'All courses'], ['pub', 'Public only']]} />
            </div>
            <div className="stats-grid stats-g4">
                <StatTile value={<>{view.played}<span className="stats-of">/{view.total}</span></>} label="Best in State courses played" sub={`${label}${publicOnly ? ' · public only' : ''}`} />
                <StatTile value={<>{view.started}<span className="stats-of">/{view.rows.length}</span></>} label="States with at least one" sub={publicOnly ? 'states with public courses' : undefined} />
                <StatTile
                    value={stats.byState[selected] || 0}
                    label={`Courses played in ${STATE_NAMES[selected]}`}
                    sub={`${current?.p ?? 0} of them ranked Best in State${publicOnly ? ' (public)' : ''}`}
                />
                <StatTile className="stats-tile-name" value={STATE_NAMES[selected]} />
            </div>

            <div className="stats-grid stats-wide">
                <StatCard title="Click a state" aside={`Best in State, ${label}`}>
                    <StateMap layer="bis" byState={stats.byState} bis={view} selected={selected} onSelect={setPicked} />
                    <div className="stats-legend"><span>Gold = Best in State courses played / ranked{publicOnly ? ' (public only)' : ''}</span></div>
                </StatCard>
                <StatCard title={STATE_NAMES[selected]} aside={`${current?.p ?? 0}/${current?.t ?? 0} played${publicOnly ? ' · public' : ''}`}>
                    <div className="stats-scroll tall">
                        {current?.entries.length
                            ? current.entries.map(e => (
                                <CourseRow key={e.course_id} played={e.played} rank={`#${e.rank_label || e.rank}`} name={shortName(e.name)} sub={e.city} tag={e.access === 'private' ? 'private' : null} />
                            ))
                            : <div className="stats-muted">No public courses ranked in this state.</div>}
                    </div>
                </StatCard>
            </div>

            <StatCard title="Progress by state" aside={<Seg label="Chart style" value={chart} onChange={setChart} options={CHARTS} />}>
                <div className="stats-chart-top">
                    <span className="stats-chart-info">{CHART_INFO[chart]}</span>
                    {sortable && <Seg label="Sort" value={sort} onChange={setSort} options={SORTS} />}
                </div>
                {chart === 'bars' && <BarsChart rows={rows} />}
                {chart === 'pips' && <PipsChart rows={rows} publicOnly={publicOnly} />}
                {chart === 'size' && <SizeChart rows={rows} publicOnly={publicOnly} />}
                {chart === 'scatter' && <ScatterChart rows={rows} />}
                {chart === 'tiers' && <TiersChart rows={rows} />}
            </StatCard>
        </>
    );
}
