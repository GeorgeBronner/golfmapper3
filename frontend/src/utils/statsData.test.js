import { describe, it, expect } from 'vitest';
import {
    buildStats, buildBestInState, buildJourney, defaultBestInStateCode, entriesIn, playedRows,
    playedInState, sortBestInState, tierCell, RANK_TIERS, listShortName, isStateList,
} from './statsData';

const course = (over) => ({ id: 1, display_name: 'A', club_name: 'A', country: 'USA', state: 'SC', year: 2020, ...over });

describe('buildStats', () => {
    it('counts courses, clubs, states and countries', () => {
        const s = buildStats([
            course({ id: 1, club_name: 'Kiawah', state: 'SC' }),
            course({ id: 2, club_name: 'Kiawah', state: 'SC' }),
            course({ id: 3, club_name: 'Pebble', state: 'CA' }),
            course({ id: 4, club_name: 'St Andrews', country: 'GBR', state: 'FIF' }),
        ], null);
        expect(s).toMatchObject({ total: 4, clubs: 3, states: 2, countries: 2, byState: { SC: 2, CA: 1 } });
        expect(s.list).toBeNull();
    });

    it('only counts US states, not DC, territories or other countries, toward the 50', () => {
        const s = buildStats([
            course({ id: 1, state: 'DC' }), course({ id: 2, state: 'PR' }), course({ id: 3, country: 'CAN', state: 'ON' }),
        ], null);
        expect(s.states).toBe(0);
    });

    it('spans every year from first to last, including empty ones, and counts undated courses', () => {
        const s = buildStats([course({ id: 1, year: 2018 }), course({ id: 2, year: 2020 }), course({ id: 3, year: null })], null);
        expect(s.years.map(y => [y.year, y.other])).toEqual([[2018, 1], [2019, 0], [2020, 1]]);
        expect(s.undated).toBe(1);
    });

    it('splits each year into ranked and other courses and never goes negative', () => {
        const courses = [course({ id: 1, year: 2020 }), course({ id: 2, year: 2020 })];
        const progress = {
            name: 'Top Public', ever_listed: 9,
            current: { label: '2025-26', total: 100, played: 1, by_state: { SC: { ranked: 3, played: 1 } }, by_country: { USA: { ranked: 3, played: 1 } } },
            courses: [
                { course_id: 1, year: 2020, current_rank: 5, name: 'A' },
                // not in the course list (no coordinates): still counted as ranked
                { course_id: 9, year: 2020, current_rank: null, name: 'B' },
                { course_id: 8, year: 2019, current_rank: null, name: 'C' },
            ],
        };
        const s = buildStats(courses, progress);
        expect(s.years).toEqual([{ year: 2019, ranked: 1, other: 0 }, { year: 2020, ranked: 2, other: 0 }]);
        expect(s.list).toMatchObject({ size: 100, played: 1, everPlayed: 3, everListed: 9, byCountry: { USA: { ranked: 3, played: 1 } } });
        expect(s.list.highest.map(c => c.course_id)).toEqual([1]);
    });

    it('counts a course once, with its latest year, when it was logged twice', () => {
        const s = buildStats([
            course({ id: 1, year: 2018 }), course({ id: 1, year: 2022 }), course({ id: 1, year: null }),
        ], null);
        expect(s).toMatchObject({ total: 1, byState: { SC: 1 }, undated: 0 });
        expect(s.years).toEqual([{ year: 2022, ranked: 0, other: 1 }]);
    });

    it('matches states and countries regardless of case and padding', () => {
        const s = buildStats([
            course({ id: 1, state: 'ca', country: 'usa' }),
            course({ id: 2, state: ' SC ', country: 'USA ' }),
            course({ id: 3, state: 'XX', country: 'USA' }),
        ], null);
        expect(s).toMatchObject({ states: 2, countries: 1, byState: { CA: 1, SC: 1 } });
    });

    it('keeps unranked courses visible in a year that also has a ranked course', () => {
        const courses = [course({ id: 1, year: 2020 }), course({ id: 2, year: 2020 })];
        const progress = {
            name: 'x', ever_listed: 1,
            current: { label: 'l', total: 100, played: 1, by_state: {} },
            courses: [{ course_id: 1, year: 2020, current_rank: 3, name: 'A' }],
        };
        expect(buildStats(courses, progress).years).toEqual([{ year: 2020, ranked: 1, other: 1 }]);
    });
});

describe('lists', () => {
    it('names the lists the picker shows and recognises Best in State lists', () => {
        expect(listShortName({ scope: 'us-public', name: 'America\'s 100 Greatest Public Courses' })).toBe('US Public');
        expect(listShortName({ scope: 'something-new', name: 'Something New' })).toBe('Something New');
        expect(isStateList({ scope: 'us-state-SC' })).toBe(true);
        expect(isStateList({ scope: 'world' })).toBe(false);
    });
});

describe('playedRows', () => {
    const stats = {
        byState: { AA: 3, BB: 9, CC: 3, DD: 1 },
        byCountry: { USA: 200, GBR: 7, IRL: 2 },
    };
    it('orders by most played, then code', () => {
        expect(playedRows(stats, false).map(r => [r.code, r.played])).toEqual([['BB', 9], ['AA', 3], ['CC', 3], ['DD', 1]]);
    });
    it('uses countries for the World list', () => {
        expect(playedRows(stats, true).map(r => r.code)).toEqual(['USA', 'GBR', 'IRL']);
    });
    it('keeps six', () => {
        const byState = Object.fromEntries(['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((c, i) => [c, i + 1]));
        expect(playedRows({ byState, byCountry: {} }, false)).toHaveLength(6);
    });
});

describe('playedInState and entriesIn', () => {
    it('lists the US courses played in a state, newest first, undated last', () => {
        const rows = playedInState([
            course({ id: 1, display_name: 'B', year: 2019 }), course({ id: 2, display_name: 'A', year: 2022 }),
            course({ id: 3, display_name: 'C', year: null }), course({ id: 4, state: 'CA' }),
            course({ id: 5, country: 'IRL', state: 'SC' }),
        ], 'SC');
        expect(rows.map(c => c.id)).toEqual([2, 1, 3]);
    });

    it('does not mistake a non-US regional code for a US state', () => {
        const entries = [
            { course_id: 1, country: 'IRL', state: 'KY' },
            { course_id: 2, country: 'USA', state: 'KY' },
        ];
        expect(entriesIn(entries, 'KY', false).map(e => e.course_id)).toEqual([2]);
        expect(entriesIn(entries, 'IRL', true).map(e => e.course_id)).toEqual([1]);
    });
});

describe('buildJourney', () => {
    const progress = {
        courses: [
            { course_id: 1, name: 'A', year: 2018, current_rank: 5 },
            { course_id: 2, name: 'B', year: 2018, current_rank: null },
            { course_id: 3, name: 'C', year: 2020, current_rank: 2 },
            { course_id: 4, name: 'D', year: null, current_rank: 9 },
        ],
    };
    it('builds a newest-first timeline with ranked courses first', () => {
        const j = buildJourney(progress, [{ year: 2018, ranked: 2, other: 3 }]);
        expect(j.timeline.map(y => y.year)).toEqual([2020, 2018]);
        expect(j.timeline[1].courses.map(c => c.course_id)).toEqual([1, 2]);
        expect(j.timeline[1].playedThatYear).toBe(5);
        expect(j.undated).toBe(1);
    });
    it('runs a cumulative count through empty years', () => {
        expect(buildJourney(progress, []).cumulative).toEqual([{ year: 2018, count: 2 }, { year: 2019, count: 2 }, { year: 2020, count: 3 }]);
    });
    it('finds the biggest years and the first and latest course', () => {
        const j = buildJourney(progress, []);
        expect(j.biggest[0].year).toBe(2018);
        expect(j.first).toMatchObject({ year: 2018 });
        expect(j.latest).toMatchObject({ year: 2020 });
    });
    it('copes with no courses', () => {
        expect(buildJourney(null, [])).toMatchObject({ timeline: [], cumulative: [], first: null, latest: null });
    });
});

describe('Best in State', () => {
    const e = (rank, played, access = 'public') => ({ course_id: rank, rank, played, access });
    const states = {
        SC: { label: '2025-26', entries: [e(1, true, 'private'), e(2, true), e(3, false), e(4, false, 'private')] },
        CA: { label: '2025-26', entries: [e(1, false), e(2, false)] },
        WY: { label: '2025-26', entries: [e(1, false, 'private')] },
    };

    it('counts played and total, with private courses and without', () => {
        const all = buildBestInState(states, false);
        expect(all).toMatchObject({ played: 2, total: 7, started: 1 });
        expect(all.byCode.SC).toMatchObject({ t: 4, p: 2, best: 1, leftPub: 1, leftPriv: 1 });
    });

    it('computes every number from public courses only when asked', () => {
        const pub = buildBestInState(states, true);
        expect(pub).toMatchObject({ played: 1, total: 4, started: 1 });
        expect(pub.byCode.SC).toMatchObject({ t: 2, p: 1, best: 2, leftPub: 1, leftPriv: 0 });
        // A state with only private courses drops out.
        expect(pub.byCode.WY).toBeUndefined();
        expect(pub.rows).toHaveLength(2);
    });

    it('sorts by completion, by left to play and alphabetically', () => {
        const rows = buildBestInState(states, false).rows;
        expect(sortBestInState(rows, 'pct')[0].code).toBe('SC');
        expect(sortBestInState(rows, 'left')[0].code).toBe('SC');
        expect(sortBestInState(rows, 'az').map(r => r.code)).toEqual(['CA', 'SC', 'WY']);
    });

    it('counts played courses per rank tier', () => {
        const row = buildBestInState({ SC: { entries: [e(1, true), e(6, true), e(7, false), e(25, false)] } }, false).rows[0];
        expect(RANK_TIERS.map(t => tierCell(row, t))).toEqual([{ t: 1, p: 1 }, { t: 2, p: 1 }, { t: 0, p: 0 }, { t: 1, p: 0 }]);
    });

    it('opens on the state with the most courses played', () => {
        expect(defaultBestInStateCode(buildBestInState(states, false).rows)).toBe('SC');
        expect(defaultBestInStateCode([])).toBeNull();
    });
});
