import { STATE_CODES, STATE_NAMES } from './usStates';

const STATE_SET = new Set(STATE_CODES);

const norm = (value) => (value || '').trim().toUpperCase();

// courses.country holds ISO 3166 alpha-3 codes; show names for the ones the ranking lists use.
export const COUNTRY_NAMES = {
    GBR: 'Great Britain & N. Ireland', IRL: 'Ireland', USA: 'United States', CAN: 'Canada', AUS: 'Australia',
    NZL: 'New Zealand', JPN: 'Japan', FRA: 'France', DOM: 'Dominican Republic', NLD: 'Netherlands',
    MEX: 'Mexico', LCA: 'St. Lucia', ESP: 'Spain', BMU: 'Bermuda', KOR: 'South Korea', ARE: 'UAE',
    SGP: 'Singapore', ZAF: 'South Africa', PRT: 'Portugal', DEU: 'Germany', ITA: 'Italy', SWE: 'Sweden',
    CHN: 'China', THA: 'Thailand', VNM: 'Vietnam', ARG: 'Argentina', CHL: 'Chile', IND: 'India',
};
export const countryName = (code) => COUNTRY_NAMES[code] || code;

// Short names for the picker. Anything else falls back to the list's own name.
const LIST_SHORT_NAMES = { 'us-public': 'US Public', 'us-all': 'US All', world: 'World' };
export const listShortName = (list) => LIST_SHORT_NAMES[list.scope] || list.name;
export const isStateList = (list) => (list.scope || '').startsWith('us-state-');
export const isWorldList = (list) => list?.scope === 'world';

// Databases without uq_user_course can hold a course more than once; count it
// once, with its latest year, as the progress endpoint does.
function uniqueCourses(courses) {
    const byId = new Map();
    for (const c of courses) {
        const seen = byId.get(c.id);
        if (!seen || (c.year || 0) > (seen.year || 0)) byId.set(c.id, c);
    }
    return [...byId.values()];
}

/**
 * Turns the user's courses (`/user_courses/readall_ids_w_year`) and, when the
 * rankings are loaded, their progress on one list (`/rankings/lists/{id}/progress`)
 * into everything the Overview shows.
 */
export function buildStats(allCourses, progress) {
    const courses = uniqueCourses(allCourses);
    const byState = {};
    const byCountry = {};
    const countries = new Set();
    const clubs = new Set();
    const byYear = {};
    let undated = 0;

    for (const c of courses) {
        const country = norm(c.country);
        const state = norm(c.state);
        if (country) { countries.add(country); byCountry[country] = (byCountry[country] || 0) + 1; }
        clubs.add(c.club_name || c.display_name);
        if (country === 'USA' && STATE_SET.has(state)) byState[state] = (byState[state] || 0) + 1;
        if (c.year) byYear[c.year] = (byYear[c.year] || 0) + 1;
        else undated += 1;
    }

    const ranked = progress?.courses ?? [];
    const rankedByYear = {};
    for (const c of ranked) if (c.year) rankedByYear[c.year] = (rankedByYear[c.year] || 0) + 1;

    // Both lists now cover every course the user has played, but guard the
    // subtraction so a year's total never drops below its ranked count.
    const dated = Object.keys({ ...byYear, ...rankedByYear }).map(Number);
    const years = [];
    if (dated.length) {
        for (let y = Math.min(...dated); y <= Math.max(...dated); y++) {
            const gold = rankedByYear[y] || 0;
            years.push({ year: y, ranked: gold, other: Math.max((byYear[y] || 0) - gold, 0) });
        }
    }

    const current = progress?.current ?? null;
    return {
        total: courses.length,
        states: Object.keys(byState).length,
        countries: countries.size,
        clubs: clubs.size,
        byState,
        byCountry,
        undated,
        years,
        list: current && {
            label: current.label,
            listName: progress.name,
            size: current.total,
            played: current.played,
            everPlayed: ranked.length,
            everListed: progress.ever_listed,
            byState: current.by_state ?? {},
            byCountry: current.by_country ?? {},
            highest: ranked.filter(c => c.current_rank).slice(0, 5),
        },
    };
}

/** Where have you played the most? Countries for the World list, US states otherwise. */
export function playedRows(stats, world, limit = 6) {
    const source = world ? stats.byCountry : stats.byState;
    return Object.entries(source)
        .filter(([code]) => code)
        .map(([code, played]) => ({ code, played }))
        .sort((a, b) => b.played - a.played || a.code.localeCompare(b.code))
        .slice(0, limit);
}

/** The user's played courses in one US state, newest year first (undated last). */
export function playedInState(courses, code) {
    return uniqueCourses(courses)
        .filter(c => norm(c.country) === 'USA' && norm(c.state) === code)
        .sort((a, b) => (b.year || 0) - (a.year || 0) || a.display_name.localeCompare(b.display_name));
}

/** Entries of the current edition that sit in one US state, or in one country for the World list. */
export function entriesIn(entries, code, world) {
    return entries.filter(e => (world ? norm(e.country) === code : norm(e.country) === 'USA' && norm(e.state) === code));
}

/** Played-by-year course lists and the cumulative curve for the Journey tab. */
export function buildJourney(progress, years) {
    const courses = progress?.courses ?? [];
    const byYear = {};
    for (const c of courses) if (c.year) (byYear[c.year] = byYear[c.year] || []).push(c);
    const ys = Object.keys(byYear).map(Number).sort((a, b) => a - b);
    const sortCourses = (list) => list.slice().sort((a, b) => (a.current_rank ?? 9999) - (b.current_rank ?? 9999) || a.name.localeCompare(b.name));

    const cumulative = [];
    if (ys.length) {
        let run = 0;
        for (let y = ys[0]; y <= ys[ys.length - 1]; y++) {
            run += (byYear[y] || []).length;
            cumulative.push({ year: y, count: run });
        }
    }
    const playedThatYear = Object.fromEntries((years || []).map(y => [y.year, y.ranked + y.other]));
    const timeline = [...ys].reverse().map(year => ({ year, courses: sortCourses(byYear[year]), playedThatYear: playedThatYear[year] || 0 }));
    const biggest = timeline.slice().sort((a, b) => b.courses.length - a.courses.length || b.year - a.year).slice(0, 5);
    return {
        timeline,
        cumulative,
        biggest,
        first: timeline.length ? { year: timeline[timeline.length - 1].year, course: timeline[timeline.length - 1].courses[0] } : null,
        latest: timeline.length ? { year: timeline[0].year, course: timeline[0].courses[0] } : null,
        undated: courses.filter(c => !c.year).length,
    };
}

/**
 * Best in State rows (one per state) from `/rankings/states/progress`.
 * With `publicOnly`, every number is computed from the public courses only, so the
 * tiles, map and charts cannot disagree.
 */
export function buildBestInState(states, publicOnly) {
    const rows = Object.entries(states || {}).map(([code, s]) => {
        const entries = s.entries.filter(e => !publicOnly || e.access !== 'private');
        const played = entries.filter(e => e.played);
        return {
            code,
            name: STATE_NAMES[code] || code,
            entries,
            t: entries.length,
            p: played.length,
            best: played.length ? Math.min(...played.map(e => e.rank)) : null,
            leftPub: entries.filter(e => !e.played && e.access !== 'private').length,
            leftPriv: entries.filter(e => !e.played && e.access === 'private').length,
        };
    }).filter(r => r.t > 0);
    return {
        rows,
        byCode: Object.fromEntries(rows.map(r => [r.code, r])),
        played: rows.reduce((a, r) => a + r.p, 0),
        total: rows.reduce((a, r) => a + r.t, 0),
        started: rows.filter(r => r.p > 0).length,
    };
}

const SORTS = {
    pct: (a, b) => b.p / b.t - a.p / a.t || b.p - a.p || a.name.localeCompare(b.name),
    left: (a, b) => (b.t - b.p) - (a.t - a.p) || b.t - a.t || a.name.localeCompare(b.name),
    az: (a, b) => a.name.localeCompare(b.name),
};
export const sortBestInState = (rows, how) => rows.slice().sort(SORTS[how] || SORTS.pct);

// How the user does at each level of a state's ranking.
export const RANK_TIERS = [[1, 5, 'Top 5'], [6, 10, '6-10'], [11, 20, '11-20'], [21, Infinity, '21+']];

export function tierCell(row, [from, to]) {
    const entries = row.entries.filter(e => e.rank >= from && e.rank <= to);
    return { t: entries.length, p: entries.filter(e => e.played).length };
}

/** The state with the most Best in State courses played (the page opens on it). */
export function defaultBestInStateCode(rows) {
    if (!rows.length) return null;
    return rows.slice().sort((a, b) => b.p - a.p || a.name.localeCompare(b.name))[0].code;
}
