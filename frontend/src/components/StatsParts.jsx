import React from 'react';
import { US_GRID, STATE_NAMES } from '../utils/usStates';
import { countryName } from '../utils/statsData';

export function StatCard({ title, aside, children, className = '' }) {
    return (
        <div className={`stats-card ${className}`.trim()}>
            {(title || aside) && (
                <div className="stats-card-head">
                    <h3>{title}</h3>
                    {aside && <span>{aside}</span>}
                </div>
            )}
            {children}
        </div>
    );
}

export function StatTile({ value, label, sub, className = '' }) {
    return (
        <div className={`stats-tile ${className}`.trim()}>
            <div className="stats-tile-value">{value}</div>
            {label && <div className="stats-tile-label">{label}</div>}
            {sub && <div className="stats-tile-sub">{sub}</div>}
        </div>
    );
}

/** Pill-shaped single-choice control. `options` is [[value, label], ...]. */
export function Seg({ options, value, onChange, label }) {
    return (
        <span className="stats-seg" role="group" aria-label={label}>
            {options.map(([v, text]) => (
                <button key={v} type="button" className={v === value ? 'on' : ''} aria-pressed={v === value} onClick={() => onChange(v)}>{text}</button>
            ))}
        </span>
    );
}

export function Tabs({ options, value, onChange }) {
    return (
        <div className="stats-tabs" role="tablist">
            {options.map(([v, text]) => (
                <button key={v} type="button" role="tab" aria-selected={v === value} className={v === value ? 'on' : ''} onClick={() => onChange(v)}>{text}</button>
            ))}
        </div>
    );
}

export function Ring({ pct, size = 120, stroke = 12, children }) {
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const mid = size / 2;
    return (
        <div className="stats-ring" style={{ width: size, height: size }}>
            <svg width={size} height={size} aria-hidden="true">
                <circle cx={mid} cy={mid} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
                <circle
                    cx={mid} cy={mid} r={r} fill="none" stroke="var(--stats-gold)" strokeWidth={stroke}
                    strokeLinecap="round" strokeDasharray={`${c * Math.min(pct, 1)} ${c}`}
                    transform={`rotate(-90 ${mid} ${mid})`}
                />
            </svg>
            <div className="stats-ring-center">{children}</div>
        </div>
    );
}

export function HBar({ label, value, max, right, green = false }) {
    return (
        <div className="stats-hbar">
            <span className="stats-hbar-label">{label}</span>
            <span className="stats-hbar-track">
                <span className={green ? 'g' : ''} style={{ width: `${max ? Math.max((value / max) * 100, value ? 2 : 0) : 0}%` }} />
            </span>
            <span className="stats-hbar-val">{right ?? value}</span>
        </div>
    );
}

const courseShade = (n) => {
    const t = 0.28 + Math.min(Math.log(n + 1) / Math.log(40), 1) * 0.72;
    return `color-mix(in srgb, var(--primary) ${Math.round(t * 100)}%, white)`;
};

/**
 * Tile-grid map of the US. Layers: "courses" shades states by how many courses you've
 * played; "list" by how many of the current list's courses in that state you've played;
 * "bis" by Best in State progress (`bis` is `buildBestInState(...)`, which also honours
 * Public only). `onSelect(code)` makes the tiles clickable; `selected` outlines one.
 */
export function StateMap({ layer, byState, list, bis, onSelect, selected }) {
    return (
        <div className="stats-map">
            {US_GRID.map(([code, x, y]) => {
                const n = byState[code] || 0;
                const t = list?.byState[code];
                const b = bis?.byCode[code];
                const name = STATE_NAMES[code];
                let cls = '';
                let bg;
                let sub = null;
                let title = `${name}: ${n} course${n === 1 ? '' : 's'}`;

                if (layer === 'list') {
                    if (!t) { cls = 'dim'; title = `${name}: no ranked courses`; }
                    else if (t.played) {
                        cls = 'on gold';
                        bg = `color-mix(in srgb, var(--stats-gold) ${Math.min(40 + t.played * 20, 100)}%, white)`;
                        sub = `${t.played}/${t.ranked}`;
                    } else { cls = 'amber'; sub = `0/${t.ranked}`; }
                    if (t) title = `${name}: ${t.played} of ${t.ranked} ranked courses played`;
                } else if (layer === 'bis') {
                    if (!b) { cls = 'dim'; title = `${name}: no ranked courses`; }
                    else {
                        if (b.p) {
                            cls = 'on gold';
                            bg = `color-mix(in srgb, var(--stats-gold) ${Math.round(25 + (b.p / b.t) * 75)}%, white)`;
                        } else cls = 'amber';
                        sub = `${b.p}/${b.t}`;
                        title = `${name}: ${b.p} of ${b.t} Best in State courses played`;
                    }
                } else if (n) {
                    cls = 'on';
                    bg = courseShade(n);
                    sub = t?.played ? `${n} · ★${t.played}` : n;
                }
                if (selected === code) cls += ' sel';
                const style = { gridColumn: x + 1, gridRow: y + 1, background: bg };
                const inner = (<><b>{code}</b>{sub != null && <i>{sub}</i>}</>);
                return onSelect
                    ? <button key={code} type="button" className={`stats-state click ${cls}`} style={style} title={title} aria-pressed={selected === code} onClick={() => onSelect(code)}>{inner}</button>
                    : <div key={code} className={`stats-state ${cls}`} style={style} title={title}>{inner}</div>;
            })}
        </div>
    );
}

/** World list: the courses are outside the US, so show countries instead of the US tile map. */
export function CountryTiles({ byCountry, onSelect, selected }) {
    const rows = Object.entries(byCountry).filter(([code]) => code).sort((a, b) => b[1].ranked - a[1].ranked || a[0].localeCompare(b[0]));
    return (
        <div className="stats-countries">
            {rows.map(([code, v]) => (
                <button
                    key={code} type="button" aria-pressed={selected === code}
                    className={`stats-country ${v.played ? 'on' : 'amber'} ${selected === code ? 'sel' : ''}`}
                    style={v.played ? { background: `color-mix(in srgb, var(--stats-gold) ${Math.min(30 + (v.played / v.ranked) * 90, 100)}%, white)` } : undefined}
                    title={`${countryName(code)}: ${v.played} of ${v.ranked} ranked courses played`}
                    onClick={() => onSelect(code)}
                >
                    <b>{countryName(code)}</b><i>{v.played}/{v.ranked}</i>
                </button>
            ))}
        </div>
    );
}

/** Stacked columns; each row is {year, ranked, other}, ranked on top. `cumulative` plots the running total. */
export function YearColumns({ rows, height = 150, cumulative = false }) {
    let run = 0;
    const data = rows.map(r => {
        const total = r.ranked + r.other;
        run += total;
        return { ...r, total, shown: cumulative ? run : total };
    });
    const max = Math.max(...data.map(r => r.shown), 1);
    return (
        <div className="stats-cols" style={{ height }}>
            {data.map(r => (
                <div key={r.year} className="stats-col" title={`${r.year}: ${r.total} course${r.total === 1 ? '' : 's'}${r.ranked ? `, ${r.ranked} on the list` : ''}`}>
                    <span className="stats-col-n">{r.shown || ''}</span>
                    <span className="stats-col-stack" style={{ height: `${(r.shown / max) * 100}%` }}>
                        <span style={{ flex: r.ranked, background: 'var(--stats-gold)' }} />
                        <span style={{ flex: r.other, background: 'var(--primary)' }} />
                    </span>
                    <span className="stats-col-l">{String(r.year).slice(-2)}</span>
                </div>
            ))}
        </div>
    );
}

/** Cumulative line chart; `points` is [{year, count}]. */
export function LineChart({ points }) {
    if (points.length < 2) return <div className="stats-muted">Play courses in two different years to see a trend.</div>;
    const W = 560, H = 170, P = 26;
    const max = Math.max(points[points.length - 1].count, 4);
    const y0 = points[0].year;
    const y1 = points[points.length - 1].year;
    const x = (year) => P + ((year - y0) / (y1 - y0)) * (W - P * 2);
    const y = (v) => H - P - (v / max) * (H - P * 2);
    const path = points.map(p => `${x(p.year)},${y(p.count)}`).join(' L');
    const last = points[points.length - 1];
    return (
        <svg className="stats-line" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${last.count} courses played in total by ${last.year}`}>
            {[0, 0.5, 1].map(f => (
                <g key={f}>
                    <line x1={P} x2={W - P} y1={y(max * f)} y2={y(max * f)} stroke="var(--border)" />
                    <text x="2" y={y(max * f) + 3}>{Math.round(max * f)}</text>
                </g>
            ))}
            <path d={`M${x(y0)},${y(0)} L${path} L${x(y1)},${y(0)}Z`} fill="var(--stats-gold)" opacity=".12" />
            <path d={`M${path}`} fill="none" stroke="var(--stats-gold)" strokeWidth="3" strokeLinejoin="round" />
            {points.filter((p, i) => i % 2 === 0 || i === points.length - 1).map(p => (
                <text key={p.year} x={x(p.year) - 8} y={H - 8}>{p.year}</text>
            ))}
            <circle cx={x(y1)} cy={y(last.count)} r="5" fill="var(--stats-gold)" />
        </svg>
    );
}
