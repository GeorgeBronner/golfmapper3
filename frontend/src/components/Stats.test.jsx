import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import Stats from './Stats';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));

const courses = [
    { id: 1, display_name: 'Pebble Beach - Pebble Beach Golf Links', club_name: 'Pebble Beach', country: 'USA', state: 'CA', city: 'Pebble Beach', year: 2019 },
    { id: 2, display_name: 'Local Muni', club_name: 'Local Muni', country: 'USA', state: 'SC', year: null },
];
const lists = [
    { id: 1, scope: 'us-public', name: 'Top Public', size: 100 },
    { id: 3, scope: 'world', name: 'World 100', size: 100 },
    { id: 9, scope: 'us-state-SC', name: 'Best Courses in South Carolina', size: null },
];
const publicProgress = {
    list_id: 1, name: 'Top Public', size: 100, ever_listed: 165,
    current: {
        id: 11, label: '2025-26', total: 100, played: 1,
        by_state: { CA: { ranked: 7, played: 1 }, WI: { ranked: 11, played: 0 } },
        by_country: { USA: { ranked: 18, played: 1 } },
    },
    editions: [],
    courses: [{ course_id: 1, name: 'Pebble Beach - Pebble Beach Golf Links', state: 'CA', country: 'USA', year: 2019, current_rank: 1, ranks: { '2025-26': 1 } }],
};
const worldProgress = {
    list_id: 3, name: 'World 100', size: 100, ever_listed: 141,
    current: {
        id: 12, label: '2026-27', total: 100, played: 0,
        by_state: {},
        // Irish courses carry the regional code KY: they must show up under Ireland, never as Kentucky.
        by_country: { GBR: { ranked: 42, played: 0 }, IRL: { ranked: 11, played: 0 } },
    },
    editions: [], courses: [],
};
const entries = {
    11: [
        { course_id: 1, rank: 1, name: 'Pebble Beach - Pebble Beach Golf Links', city: 'Pebble Beach', state: 'CA', country: 'USA', played: true, year: 2019 },
        { course_id: 5, rank: 2, name: 'Erin Hills', city: 'Erin', state: 'WI', country: 'USA', played: false, year: null },
    ],
    12: [{ course_id: 8, rank: 1, name: 'Ballybunion Golf Club: Old', city: 'Ballybunion', state: 'KY', country: 'IRL', played: false, year: null }],
};
const bisStates = {
    states: {
        SC: {
            label: '2025-26',
            entries: [
                { course_id: 20, rank: 1, access: 'private', name: 'Congaree', city: 'Ridgeland', played: true, year: 2021 },
                { course_id: 21, rank: 2, access: 'public', name: 'Kiawah Island - Ocean Course', city: 'Kiawah', played: false, year: null },
            ],
        },
        CA: { label: '2025-26', entries: [{ course_id: 30, rank: 1, access: 'public', name: 'Pebble Beach', city: 'Pebble Beach', played: false, year: null }] },
    },
};

const mockApi = ({ rankings = true, user = courses } = {}) =>
    api.get.mockImplementation(async url => {
        if (url === '/user_courses/readall_ids_w_year') return { data: user };
        if (!rankings) throw new Error('no rankings');
        if (url === '/rankings') return { data: lists };
        if (url === '/rankings/lists/1/progress') return { data: publicProgress };
        if (url === '/rankings/lists/3/progress') return { data: worldProgress };
        if (url === '/rankings/states/progress') return { data: bisStates };
        const edition = url.match(/^\/rankings\/editions\/(\d+)$/);
        if (edition) return { data: { entries: entries[edition[1]] } };
        throw new Error(`unexpected ${url}`);
    });

describe('Stats overview', () => {
    beforeEach(() => { api.get.mockReset(); });

    it('shows totals and progress on the first list, US Public', async () => {
        mockApi();
        render(<Stats />);
        expect(await screen.findByText('Courses played')).toBeInTheDocument();
        expect(screen.getByText('2/50')).toBeInTheDocument();
        expect(await screen.findByText('On the 2025-26 US Public list')).toBeInTheDocument();
        expect(screen.getByText('Ever on the US Public list')).toBeInTheDocument();
        expect(screen.getByText('HIGHEST RANKED PLAYED')).toBeInTheDocument();
        expect(screen.getByText('1 with no year set')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/rankings/lists/1/progress');
        expect(api.get).toHaveBeenCalledWith('/rankings/editions/11');
    });

    it('offers the top lists in the picker but not the Best in State lists', async () => {
        mockApi();
        render(<Stats />);
        const picker = await screen.findByRole('group', { name: 'Ranking list' });
        expect(within(picker).getAllByRole('button').map(b => b.textContent)).toEqual(['US Public', 'World']);
    });

    it('asks for courses without coordinates too', async () => {
        mockApi();
        render(<Stats />);
        await screen.findByText('Courses played');
        expect(api.get).toHaveBeenCalledWith('/user_courses/readall_ids_w_year', { params: { include_unmapped: true } });
    });

    it('shows the course part of a "Club - Course" name in the highest-ranked rows', async () => {
        mockApi();
        render(<Stats />);
        expect(await screen.findByText('Pebble Beach Golf Links')).toBeInTheDocument();
    });

    it('uses the singular for a single club', async () => {
        mockApi({ user: [courses[0]] });
        render(<Stats />);
        expect(await screen.findByText('at 1 club')).toBeInTheDocument();
    });

    it('lists the courses in a state when it is clicked', async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByTitle('Wisconsin: 0 of 11 ranked courses played'));
        expect(await screen.findByText('Wisconsin · US Public 2025-26')).toBeInTheDocument();
        expect(screen.getByText('Erin Hills')).toBeInTheDocument();
        // Clicking the same state again, or Close, returns to the gaps card.
        fireEvent.click(screen.getByRole('button', { name: 'close ✕' }));
        expect(screen.getByText('Most still to play, by state')).toBeInTheDocument();
    });

    it('lists the courses you have played in a state on the Courses layer', async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByRole('button', { name: 'Courses' }));
        fireEvent.click(screen.getByTitle('California: 1 course'));
        expect(await screen.findByText('California · played')).toBeInTheDocument();
        expect(screen.getByText('2019')).toBeInTheDocument();
    });

    it('shows countries, not US states, for the World list', async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByRole('button', { name: 'World' }));
        expect(await screen.findByTitle('Ireland: 0 of 11 ranked courses played')).toBeInTheDocument();
        expect(screen.queryByTitle(/^Kentucky/)).not.toBeInTheDocument();
        expect(screen.getByText('Most still to play, by country')).toBeInTheDocument();
        fireEvent.click(screen.getByTitle('Ireland: 0 of 11 ranked courses played'));
        expect(await screen.findByText('Ballybunion Golf Club: Old')).toBeInTheDocument();
    });

    it('still works when the rankings fail to load', async () => {
        mockApi({ rankings: false });
        render(<Stats />);
        expect(await screen.findByText('Courses played')).toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: 'Journey' })).not.toBeInTheDocument();
        expect(screen.queryByRole('group', { name: 'Ranking list' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Best in State' })).not.toBeInTheDocument();
    });

    it('invites a new user to add a course', async () => {
        mockApi({ user: [] });
        render(<Stats />);
        expect(await screen.findByText(/Add a course/)).toBeInTheDocument();
    });

    it('shows an error when the courses fail to load', async () => {
        api.get.mockImplementation(async () => { throw new Error('down'); });
        render(<Stats />);
        expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load your stats');
    });
});

describe('Stats journey', () => {
    beforeEach(() => { api.get.mockReset(); });

    it('shows the year-by-year timeline for the picked list', async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByRole('tab', { name: 'Journey' }));
        expect(await screen.findByText('Year by year')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /^2019/ })).toBeInTheDocument();
        expect(screen.getByText('Biggest years')).toBeInTheDocument();
    });
});

describe('Stats Best in State', () => {
    beforeEach(() => { api.get.mockReset(); });

    const openTab = async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByRole('tab', { name: 'Best in State' }));
        await screen.findByText('Best in State courses played');
    };

    it('loads Best in State only when the tab opens, and hides the list picker there', async () => {
        mockApi();
        render(<Stats />);
        await screen.findByText('Courses played');
        expect(api.get).not.toHaveBeenCalledWith('/rankings/states/progress');
        fireEvent.click(screen.getByRole('tab', { name: 'Best in State' }));
        await screen.findByText('Best in State courses played');
        expect(api.get).toHaveBeenCalledWith('/rankings/states/progress');
        expect(screen.queryByRole('group', { name: 'Ranking list' })).not.toBeInTheDocument();
    });

    it('opens on the state with the most courses played and lists its courses', async () => {
        await openTab();
        expect(screen.getByText('1/2 played')).toBeInTheDocument();
        expect(screen.getByText('Congaree')).toBeInTheDocument();
        expect(screen.getAllByText('South Carolina').length).toBeGreaterThan(0);
    });

    it('recomputes every number when Public only is on', async () => {
        await openTab();
        const tile = () => screen.getByText('Best in State courses played').closest('.stats-tile');
        expect(tile()).toHaveTextContent('1/3');
        fireEvent.click(screen.getByRole('button', { name: 'Public only' }));
        // Congaree is private and the only course played: nothing is left played, and it is hidden.
        expect(screen.queryByText('Congaree')).not.toBeInTheDocument();
        expect(tile()).toHaveTextContent('0/2');
        expect(screen.getByText('2025-26 · public only')).toBeInTheDocument();
        expect(screen.getByText('0 of them ranked Best in State (public)')).toBeInTheDocument();
    });

    it('switches the Progress by state chart style', async () => {
        await openTab();
        fireEvent.click(screen.getByRole('button', { name: 'Course pips' }));
        expect(screen.getByText(/One square per ranked course/)).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Rank tiers' }));
        expect(screen.getByText('Top 5')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Scatter' }));
        expect(screen.getByRole('img', { name: /Best in State progress by state size/ })).toBeInTheDocument();
    });

    it('selects another state from the map', async () => {
        await openTab();
        fireEvent.click(screen.getByTitle('California: 0 of 1 Best in State courses played'));
        expect(await screen.findByText('Pebble Beach')).toBeInTheDocument();
    });
});
