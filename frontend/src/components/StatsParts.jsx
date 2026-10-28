import React from 'react';
import { US_GRID, STATE_NAMES } from '../utils/usStates';

export function StatCard({ title, aside, children }) {
    return (
        <div className="stats-card">
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

export function StatTile({ value, label, sub }) {
    return (
        <div className="stats-tile">
            <div className="stats-tile-value">{value}</div>
            <div className="stats-tile-label">{label}</div>
            {sub && <div className="stats-tile-sub">{sub}</div>}
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

export function HBar({ label, value, max, right }) {
    return (
        <div className="stats-hbar">
            <span className="stats-hbar-label">{label}</span>
            <span className="stats-hbar-track">
                <span style={{ width: `${max ? Math.max((value / max) * 100, value ? 2 : 0) : 0}%` }} />
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
 * Tile-grid map of the US. "courses" shades states by how many courses you've
 * played (starred when that includes Top 100 courses); "top100" shades them by
 * how many of the current list's courses in that state you've played.
 */
export function StateMap({ layer, byState, top100 }) {
    return (
        <div className="stats-map">
            {US_GRID.map(([code, x, y]) => {
                const n = byState[code] || 0;
                const t = top100?.byState[code];
                let cls = '';
                let bg;
                let sub = null;
                let title = `${STATE_NAMES[code]}: ${n} course${n === 1 ? '' : 's'}`;

                if (layer === 'top100') {
                    if (!t) { cls = 'dim'; title = `${STATE_NAMES[code]}: no ranked courses`; }
                    else if (t.played) {
                        cls = 'on gold';
                        bg = `color-mix(in srgb, var(--stats-gold) ${Math.min(40 + t.played * 20, 100)}%, white)`;
                        sub = `${t.played}/${t.ranked}`;
                    } else { cls = 'amber'; sub = `0/${t.ranked}`; }
                    if (t) title = `${STATE_NAMES[code]}: ${t.played} of ${t.ranked} ranked courses played`;
                } else if (n) {
                    cls = 'on';
                    bg = courseShade(n);
                    sub = t?.played ? `${n} · ★${t.played}` : n;
                }

                return (
                    <div key={code} className={`stats-state ${cls}`} style={{ gridColumn: x + 1, gridRow: y + 1, background: bg }} title={title}>
                        <b>{code}</b>
                        {sub != null && <i>{sub}</i>}
                    </div>
                );
            })}
        </div>
    );
}

/** Stacked columns; each row is {year, ranked, other}, ranked on top. */
export function YearColumns({ rows, height = 150 }) {
    const max = Math.max(...rows.map(r => r.ranked + r.other), 1);
    return (
        <div className="stats-cols" style={{ height }}>
            {rows.map(r => {
                const total = r.ranked + r.other;
                return (
                    <div key={r.year} className="stats-col" title={`${r.year}: ${total} course${total === 1 ? '' : 's'}${r.ranked ? `, ${r.ranked} Top 100` : ''}`}>
                        <span className="stats-col-n">{total || ''}</span>
                        <span className="stats-col-stack" style={{ height: `${(total / max) * 100}%` }}>
                            <span style={{ flex: r.ranked, background: 'var(--stats-gold)' }} />
                            <span style={{ flex: r.other, background: 'var(--primary)' }} />
                        </span>
                        <span className="stats-col-l">{String(r.year).slice(-2)}</span>
                    </div>
                );
            })}
        </div>
    );
}
