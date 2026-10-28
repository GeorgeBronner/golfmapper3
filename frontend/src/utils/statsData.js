import { STATE_CODES } from './usStates';

const STATE_SET = new Set(STATE_CODES);

/**
 * Turns the user's courses (`/user_courses/readall_ids_w_year`) and, when the
 * rankings are loaded, their list progress (`/rankings/lists/{id}/progress`)
 * into everything the stats page shows.
 */
export function buildStats(courses, progress) {
    const byState = {};
    const countries = new Set();
    const clubs = new Set();
    const byYear = {};
    let undated = 0;

    for (const c of courses) {
        if (c.country) countries.add(c.country);
        clubs.add(c.club_name || c.display_name);
        if (c.country === 'USA' && STATE_SET.has(c.state)) byState[c.state] = (byState[c.state] || 0) + 1;
        if (c.year) byYear[c.year] = (byYear[c.year] || 0) + 1;
        else undated += 1;
    }

    const ranked = progress?.courses ?? [];
    const rankedByYear = {};
    for (const c of ranked) if (c.year) rankedByYear[c.year] = (rankedByYear[c.year] || 0) + 1;

    // The course list leaves out courses without coordinates but the progress
    // call does not, so a year's total never drops below its ranked count.
    const dated = Object.keys({ ...byYear, ...rankedByYear }).map(Number);
    const years = [];
    if (dated.length) {
        for (let y = Math.min(...dated); y <= Math.max(...dated); y++) {
            const gold = rankedByYear[y] || 0;
            years.push({ year: y, ranked: gold, other: Math.max((byYear[y] || 0) - gold, 0) });
        }
    }

    const current = progress?.current ?? null;
    const rankedByStateCurrent = current?.by_state ?? {};
    const topStates = Object.entries(rankedByStateCurrent)
        .filter(([code]) => code)
        .sort((a, b) => b[1].ranked - a[1].ranked || a[0].localeCompare(b[0]))
        .slice(0, 6)
        .map(([code, v]) => ({ code, ...v }));

    return {
        total: courses.length,
        states: Object.keys(byState).length,
        countries: countries.size,
        clubs: clubs.size,
        byState,
        undated,
        years,
        top100: current && {
            label: current.label,
            listName: progress.name,
            size: current.total,
            played: current.played,
            everPlayed: ranked.length,
            everListed: progress.ever_listed,
            byState: rankedByStateCurrent,
            topStates,
            highest: ranked.filter(c => c.current_rank).slice(0, 5),
        },
    };
}
