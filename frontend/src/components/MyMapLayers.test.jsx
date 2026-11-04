import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import Map from './Map';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));
vi.mock('./AuthProvider', () => ({ useAuth: () => ({ token: 't' }) }));
vi.mock('./CourseMap', () => ({
    default: ({ groups, showLegend, ranks, focusPoints }) => (
        <div data-testid="course-map" data-legend={String(!!showLegend)} data-focus={focusPoints ? String(focusPoints.length) : ''}>
            {groups.map(g => (
                <section key={g.name} data-color={g.color}>
                    {g.name}: {g.points.map(p => p.name).join(', ')}
                </section>
            ))}
            <output data-testid="ranks">{JSON.stringify(ranks)}</output>
        </div>
    ),
}));

const fields = ['id', 'lat', 'lon', 'name', 'year'];
const rankFields = [...fields, 'rank', 'rank_label', 'access'];
const lists = [
    { id: 7, name: 'US Public', publisher: 'Golf Digest', scope: 'us-public', editions: [{ id: 71, label: '2025-26' }] },
    { id: 20, name: 'Best Courses in Alabama', publisher: 'Golf Digest', scope: 'us-state-AL', editions: [{ id: 201, label: '2025-26' }] },
];
// The user has played Pebble (1) and Home (9, not ranked).
const mine = [[1, 36, -121, 'Pebble', 2024], [9, 40, -90, 'Home', 2023]];
const usPublic = [[1, 36, -121, 'Pebble', 2025, 1, null, null], [2, 35, -100, 'Erin', 2025, 2, null, null]];
const alabama = [[5, 31, -87, 'Grand', 2025, 1, null, 'public'], [6, 32, -86, 'Club', 2025, 2, null, 'private']];

const mockApi = (url, config) => {
    if (url === '/map/points') return Promise.resolve({ data: { fields, points: mine } });
    if (url === '/rankings') return Promise.resolve({ data: lists });
    if (url === '/rankings/editions/71') {
        return Promise.resolve({ data: { label: '2025-26', entries: [{ course_id: 1, rank: 1 }] } });
    }
    if (url === '/map/rankings/7/points') {
        return Promise.resolve({ data: { fields: rankFields, edition: '2025-26', points: usPublic } });
    }
    if (url === '/map/rankings/20/points') {
        return Promise.resolve({ data: { fields: rankFields, edition: config.params ? '2025-26' : '', points: alabama } });
    }
    return Promise.reject(new Error(`unexpected ${url}`));
};

describe('My Map ranking layers', () => {
    beforeEach(() => {
        api.get.mockReset();
        api.get.mockImplementation(mockApi);
    });

    it('starts as it always did, with every layer off and the current rank in popups', async () => {
        render(<Map />);
        await screen.findByText(/My courses: Pebble, Home/);
        expect(screen.getByLabelText('US Public')).not.toBeChecked();
        expect(api.get).not.toHaveBeenCalledWith('/map/rankings/7/points', expect.anything());
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-legend', 'false');
        await vi.waitFor(() => expect(screen.getByTestId('ranks').textContent).toContain('Golf Digest 2025-26'));
    });

    it('draws unplayed ranked courses under My courses and played ones in a third color on top', async () => {
        const user = userEvent.setup();
        render(<Map />);
        await screen.findByText(/My courses: Pebble, Home/);
        await user.click(screen.getByLabelText('US Public'));

        const unplayed = await screen.findByText(/US Public 2025-26: Erin$/);
        const mineGroup = screen.getByText(/My courses:/);
        const played = screen.getByText(/US Public 2025-26 · played: Pebble$/);
        expect(unplayed).toHaveAttribute('data-color', '#d4a017');
        expect(played).toHaveAttribute('data-color', '#2f9e44');
        expect(mineGroup).toHaveAttribute('data-color', 'red');

        // Order in the DOM is draw order, bottom to top.
        const sections = [...screen.getByTestId('course-map').querySelectorAll('section')];
        expect(sections.indexOf(unplayed)).toBeLessThan(sections.indexOf(mineGroup));
        expect(sections.indexOf(mineGroup)).toBeLessThan(sections.indexOf(played));
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-legend', 'true');
        // Popups now list ranks from the ticked layers.
        expect(JSON.parse(screen.getByTestId('ranks').textContent)['2'][0]).toMatchObject({ rank: 2, label: 'US Public 2025-26' });
    });

    it('leaves out the unplayed group when every course in a layer has been played', async () => {
        api.get.mockImplementation((url, config) => (
            url === '/map/rankings/7/points'
                ? Promise.resolve({ data: { fields: rankFields, edition: '2025-26', points: [usPublic[0]] } })
                : mockApi(url, config)
        ));
        const user = userEvent.setup();
        render(<Map />);
        await screen.findByText(/My courses:/);
        await user.click(screen.getByLabelText('US Public'));
        expect(await screen.findByText(/US Public 2025-26 · played: Pebble$/)).toBeInTheDocument();
        // No empty "US Public 2025-26" group (and so no empty legend entry).
        expect(screen.queryByText(/^US Public 2025-26:/)).toBeNull();
    });

    it('shows the Best in State layer here too, and zooms to a single state', async () => {
        const user = userEvent.setup();
        render(<Map />);
        await screen.findByText(/My courses:/);
        await user.selectOptions(screen.getByLabelText('Best in State state'), '20');
        await user.click(screen.getByLabelText('Best in State'));
        expect(await screen.findByText(/Best Courses in Alabama 2025-26: Grand, Club/)).toBeInTheDocument();
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-focus', '2');

        await user.click(screen.getByLabelText('Public only'));
        expect(await screen.findByText(/Best Courses in Alabama 2025-26: Grand$/)).toBeInTheDocument();
    });

    it('shows the rankings bar and map even when the user has no courses yet', async () => {
        api.get.mockImplementation((url, config) => (
            url === '/map/points' ? Promise.resolve({ data: { fields, points: [] } }) : mockApi(url, config)
        ));
        const user = userEvent.setup();
        render(<Map />);
        expect(await screen.findByText(/haven't added any courses/)).toBeInTheDocument();
        await user.click(screen.getByLabelText('US Public'));
        expect(await screen.findByText(/US Public 2025-26: Pebble, Erin/)).toBeInTheDocument();
        expect(screen.queryByText(/· played/)).toBeNull();
    });
});
