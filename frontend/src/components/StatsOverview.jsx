import React, { useEffect, useState } from 'react';
import { STATE_CODES, STATE_NAMES } from '../utils/usStates';
import { countryName, entriesIn, gapRows, playedInState } from '../utils/statsData';
import { StatCard, StatTile, Ring, HBar, Seg, StateMap, CountryTiles, YearColumns } from './StatsParts';

// Shorten "Club - Course" display names to the course part for tight rows.
export const shortName = (name) => {
    const i = name.indexOf(' - ');
    return i >= 0 ? name.slice(i + 3).trim() : name;
};

export function CourseRow({ played, rank, name, sub, year, tag }) {
    return (
        <div className="stats-li">
            <span className={`stats-chk ${played ? 'on' : ''}`} aria-label={played ? 'played' : 'not played'}>{played ? '✓' : ''}</span>
            {rank && <b className="stats-rk">{rank}</b>}
            <span className="stats-li-name">{name}{sub && <span className="stats-sub"> · {sub}</span>}</span>
            {tag && <span className="stats-badge">{tag}</span>}
            {year && <span className="stats-badge p">{year}</span>}
        </div>
    );
}

// The courses behind the state (or, for the World list, country) clicked on the map.
function PlaceCard({ layer, code, courses, entries, bis, world, listName, label, onClose }) {
    let title;
    let played;
    let total = null;
    let rows;
    if (layer === 'list') {
        const list = entriesIn(entries, code, world);
        played = list.filter(e => e.played).length;
        total = list.length;
        title = `${world ? countryName(code) : STATE_NAMES[code]} · ${listName} ${label}`;
        rows = list.map(e => (
            <CourseRow key={e.course_id} played={e.played} rank={`#${e.rank_label || e.rank}`} name={shortName(e.name)} sub={e.city} year={e.played ? e.year : null} />
        ));
    } else if (layer === 'bis') {
        const list = bis?.byCode[code]?.entries ?? [];
        played = list.filter(e => e.played).length;
        total = list.length;
        title = `${STATE_NAMES[code]} · Best in State`;
        rows = list.map(e => (
            <CourseRow key={e.course_id} played={e.played} rank={`#${e.rank_label || e.rank}`} name={shortName(e.name)} sub={e.city} year={e.played ? e.year : null} tag={e.access === 'private' ? 'private' : null} />
        ));
    } else {
        const list = playedInState(courses, code);
        played = list.length;
        title = `${STATE_NAMES[code]} · played`;
        rows = list.map(c => <CourseRow key={c.id} played name={shortName(c.display_name)} sub={c.city} year={c.year} />);
    }
    return (
        <StatCard
            title={title}
            aside={<>{total != null ? `${played}/${total} played` : `${played} played`} · <button type="button" className="stats-link" onClick={onClose}>close ✕</button></>}
        >
            <div className="stats-scroll">
                {rows.length ? rows : <div className="stats-muted">{layer === 'courses' ? 'You have not played any courses in this state yet.' : 'No courses from this list here.'}</div>}
            </div>
        </StatCard>
    );
}

export default function StatsOverview({ stats, courses, list, listName, entries, world, bis, onNeedBis }) {
    const t = stats.list;
    // The list layer is the default once rankings have loaded (they arrive after the courses).
    const [layerChoice, setLayerChoice] = useState(null);
    const layer = layerChoice ?? (t ? 'list' : 'courses');
    const [selected, setSelected] = useState(null);
    const [cumulative, setCumulative] = useState(false);

    // A different list means different places to show.
    useEffect(() => { setSelected(null); }, [list?.id]);

    const changeLayer = (value) => {
        setLayerChoice(value);
        setSelected(null);
        if (value === 'bis') onNeedBis();
    };
    const toggle = (code) => setSelected(prev => (prev === code ? null : code));

    const countryMap = t && world && layer === 'list';
    const gaps = t ? gapRows(t, world) : [];
    const maxLeft = Math.max(...gaps.map(g => g.left), 1);
    const place = selected && (layer !== 'list' || entries) && (layer !== 'bis' || bis);

    return (
        <>
            <div className="stats-grid stats-g4">
                <StatTile value={stats.total} label="Courses played" sub={`at ${stats.clubs} ${stats.clubs === 1 ? 'club' : 'clubs'}`} />
                <StatTile value={`${stats.states}/${STATE_CODES.length}`} label="States" sub={`${stats.countries} ${stats.countries === 1 ? 'country' : 'countries'}`} />
                {t && (
                    <>
                        <StatTile value={<>{t.played}<span className="stats-of">/{t.size}</span></>} label={`On the ${t.label} ${listName} list`} sub="current edition" />
                        <StatTile value={<>{t.everPlayed}<span className="stats-of">/{t.everListed}</span></>} label={`Ever on the ${listName} list`} sub="every edition" />
                    </>
                )}
            </div>

            <div className="stats-grid stats-wide">
                <StatCard
                    title="Where you've played"
                    aside={t && <Seg label="Map layer" value={layer} onChange={changeLayer} options={[['courses', 'Courses'], ['list', listName], ['bis', 'Best in State']]} />}
                >
                    {layer === 'bis' && !bis && <div className="stats-muted">Loading Best in State…</div>}
                    {countryMap
                        ? <CountryTiles byCountry={t.byCountry} selected={selected} onSelect={toggle} />
                        : (layer !== 'bis' || bis) && <StateMap layer={layer} byState={stats.byState} list={t} bis={bis} selected={selected} onSelect={toggle} />}
                    <div className="stats-legend">
                        <span>Click a {countryMap ? 'country' : 'state'} to list its courses</span>
                        {layer === 'courses' && <span>Darker = more courses played</span>}
                        {layer === 'list' && <span>Gold = {listName} courses played / ranked in {world ? 'country' : 'state'} · outlined = none yet</span>}
                        {layer === 'bis' && <span>Gold = Best in State courses played / ranked in state</span>}
                    </div>
                </StatCard>

                {t && (
                    <div className="stats-stack">
                        <StatCard title={`${listName} progress`} aside={t.label}>
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
                        {place
                            ? <PlaceCard layer={layer} code={selected} courses={courses} entries={entries ?? []} bis={bis} world={world} listName={listName} label={t.label} onClose={() => setSelected(null)} />
                            : (
                                <StatCard title={`Most still to play, by ${world ? 'country' : 'state'}`} aside="left to play">
                                    {gaps.length === 0 && <div className="stats-muted">Nothing left to play here.</div>}
                                    {gaps.map(g => (
                                        <HBar key={g.code} label={world ? countryName(g.code) : g.code} value={g.left} max={maxLeft} right={`${g.left} left`} />
                                    ))}
                                </StatCard>
                            )}
                    </div>
                )}
                {!t && selected && (
                    <PlaceCard layer="courses" code={selected} courses={courses} entries={[]} onClose={() => setSelected(null)} />
                )}
            </div>

            {stats.years.length > 0 && (
                <StatCard
                    title="Courses per year"
                    aside={<Seg label="Chart type" value={cumulative ? 'cum' : 'yr'} onChange={v => setCumulative(v === 'cum')} options={[['yr', 'Per year'], ['cum', 'Cumulative']]} />}
                >
                    {stats.undated > 0 && <div className="stats-muted">{stats.undated} with no year set</div>}
                    <div className="stats-cols-wrap"><YearColumns rows={stats.years} cumulative={cumulative} /></div>
                    {t && (
                        <div className="stats-legend">
                            <span><i className="stats-dot stats-dot-gold" />{listName} courses (any edition)</span>
                            <span><i className="stats-dot" />Everything else</span>
                        </div>
                    )}
                </StatCard>
            )}
        </>
    );
}
