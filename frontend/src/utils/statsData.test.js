import { describe, it, expect } from 'vitest';
import { buildStats } from './statsData';

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
        expect(s.top100).toBeNull();
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
            current: { label: '2025-26', total: 100, played: 1, by_state: { SC: { ranked: 3, played: 1 } } },
            courses: [
                { course_id: 1, year: 2020, current_rank: 5, name: 'A' },
                // not in the course list (no coordinates): still counted as ranked
                { course_id: 9, year: 2020, current_rank: null, name: 'B' },
                { course_id: 8, year: 2019, current_rank: null, name: 'C' },
            ],
        };
        const s = buildStats(courses, progress);
        expect(s.years).toEqual([{ year: 2019, ranked: 1, other: 0 }, { year: 2020, ranked: 2, other: 0 }]);
        expect(s.top100).toMatchObject({ size: 100, played: 1, everPlayed: 3, everListed: 9 });
        expect(s.top100.highest.map(c => c.course_id)).toEqual([1]);
    });

    it('orders top states by ranked count then code and keeps six', () => {
        const by_state = Object.fromEntries(['AA', 'BB', 'CC', 'DD', 'EE', 'FF', 'GG'].map((c, i) => [c, { ranked: i === 6 ? 9 : 2, played: 0 }]));
        const s = buildStats([course()], { name: 'x', ever_listed: 1, current: { label: 'l', total: 1, played: 0, by_state }, courses: [] });
        expect(s.top100.topStates.map(t => t.code)).toEqual(['GG', 'AA', 'BB', 'CC', 'DD', 'EE']);
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
