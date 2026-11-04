import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import Map from './Map';
import AllUsersMap from './AllUsersMap';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));
vi.mock('./AuthProvider', () => ({ useAuth: () => ({ token: 't' }) }));
vi.mock('./CourseMap', () => ({
    default: ({ groups, showLegend }) => (
        <div data-testid="course-map" data-legend={String(!!showLegend)}>
            {groups.map(g => (
                <section key={g.name} data-color={g.color}>
                    {g.name}: {g.points.map(p => `${p.name} (${p.year})`).join(', ')}
                </section>
            ))}
        </div>
    ),
}));

const fields = ['id', 'lat', 'lon', 'name', 'year'];

describe('Map', () => {
    beforeEach(() => { api.get.mockReset(); });

    it("renders the user's points", async () => {
        api.get.mockResolvedValue({ data: { fields, points: [[1, 30, -88, 'Magnolia', 2024]] } });
        render(<Map />);
        expect(await screen.findByText(/Magnolia \(2024\)/)).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/map/points');
    });

    it('shows the empty state when the user has no courses', async () => {
        api.get.mockResolvedValue({ data: { fields, points: [] } });
        render(<Map />);
        expect(await screen.findByText(/haven't added any courses/)).toBeInTheDocument();
        // The map still shows, so a new user can browse the rankings layers.
        expect(screen.getByTestId('course-map')).toBeInTheDocument();
    });
});

describe('AllUsersMap', () => {
    beforeEach(() => { api.get.mockReset(); });

    it('renders one colored group per user with a legend', async () => {
        api.get.mockResolvedValue({
            data: {
                fields,
                users: [
                    { username: 'alice', points: [[1, 30, -88, 'Magnolia', 2024]] },
                    { username: 'bob', points: [[2, 31, -87, 'West', null]] },
                ],
            },
        });
        render(<AllUsersMap />);
        const alice = await screen.findByText(/alice: Magnolia/);
        const bob = screen.getByText(/bob: West/);
        expect(alice).toHaveAttribute('data-color', '#e74c3c');
        expect(bob).toHaveAttribute('data-color', '#3498db');
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-legend', 'true');
        expect(api.get).toHaveBeenCalledWith('/map/all_points');
    });

    const usersData = {
        fields,
        users: [{ username: 'alice', points: [[1, 30, -88, 'Magnolia', 2024]] }],
    };
    const rankFields = [...fields, 'rank', 'rank_label'];
    const lists = [
        { id: 7, name: 'US Public', publisher: 'Golf Digest', editions: [{ id: 71, label: '2025-26' }, { id: 70, label: '2023-24' }] },
        { id: 8, name: 'World', publisher: 'Golf Digest', editions: [{ id: 81, label: '2026-27' }] },
    ];
    // points[listId][editionId] -> compact rows; anything else rejects.
    const mockApi = (points, { rankingsFail = false } = {}) => (url, config) => {
        if (url === '/map/all_points') return Promise.resolve({ data: usersData });
        if (url === '/rankings') return Promise.resolve({ data: lists });
        const m = url.match(/^\/map\/rankings\/(\d+)\/points$/);
        const rows = m && points[m[1]]?.[config?.params?.edition_id];
        if (rankingsFail || !rows) return Promise.reject(new Error('boom'));
        const edition = lists.flatMap(l => l.editions).find(e => e.id === config.params.edition_id).label;
        return Promise.resolve({ data: { fields: rankFields, edition, points: rows } });
    };

    it('shows the first ranking list, newest edition, as a gold group after the users', async () => {
        api.get.mockImplementation(mockApi({ 7: { 71: [[2, 31, -87, 'Pebble', 2025, 1, null]] } }));
        render(<AllUsersMap />);
        const group = await screen.findByText(/US Public 2025-26: Pebble \(2025\)/);
        expect(group).toHaveAttribute('data-color', '#d4a017');
        expect(screen.getByText(/alice: Magnolia/)).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/map/rankings/7/points', { params: { edition_id: 71 } });
        expect(api.get).not.toHaveBeenCalledWith('/map/rankings/8/points', expect.anything());
    });

    it('adds another list and switches editions from the rankings bar', async () => {
        api.get.mockImplementation(mockApi({
            7: { 71: [[2, 31, -87, 'Pebble', 2025, 1, null]], 70: [[3, 32, -86, 'Erin', 2023, 1, null]] },
            8: { 81: [[4, 56, -3, 'St Andrews', 2026, 2, 'T2']] },
        }));
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByText(/US Public 2025-26: Pebble/);

        await user.click(screen.getByLabelText('World'));
        expect(await screen.findByText(/World 2026-27: St Andrews/)).toBeInTheDocument();

        await user.selectOptions(screen.getByLabelText('US Public edition'), '70');
        expect(await screen.findByText(/US Public 2023-24: Erin/)).toBeInTheDocument();
        expect(screen.queryByText(/US Public 2025-26/)).toBeNull();

        await user.click(screen.getByLabelText('World'));
        expect(screen.queryByText(/World 2026-27/)).toBeNull();
    });

    it('still shows the users when a ranking layer fails to load', async () => {
        api.get.mockImplementation(mockApi({}, { rankingsFail: true }));
        render(<AllUsersMap />);
        expect(await screen.findByText(/alice: Magnolia/)).toBeInTheDocument();
        expect(screen.queryByText(/US Public/, { selector: 'section' })).toBeNull();
        expect(await screen.findByRole('alert')).toHaveTextContent("couldn't load");
    });

    it('keeps the rankings bar and loads layers again after Refresh', async () => {
        api.get.mockImplementation(mockApi({ 7: { 71: [[2, 31, -87, 'Pebble', 2025, 1, null]] } }));
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByText(/US Public 2025-26: Pebble/);
        api.get.mockClear();

        await user.click(screen.getByText(/Refresh Map/));
        expect(await screen.findByText(/US Public 2025-26: Pebble/)).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/map/rankings/7/points', { params: { edition_id: 71 } });
    });

    it('reloads the selected layers on Refresh even when the rankings call fails', async () => {
        const points = { 7: { 71: [[2, 31, -87, 'Pebble', 2025, 1, null]] } };
        api.get.mockImplementation(mockApi(points));
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByText(/US Public 2025-26: Pebble/);

        const working = mockApi(points);
        api.get.mockClear();
        api.get.mockImplementation((url, config) => (
            url === '/rankings' ? Promise.reject(new Error('boom')) : working(url, config)
        ));
        await user.click(screen.getByText(/Refresh Map/));
        expect(await screen.findByText(/US Public 2025-26: Pebble/)).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/map/rankings/7/points', { params: { edition_id: 71 } });
    });

    it('shows an error when loading fails', async () => {
        api.get.mockImplementation(() => Promise.reject(new Error('boom')));
        render(<AllUsersMap />);
        expect(await screen.findByText(/Failed to load map/)).toBeInTheDocument();
    });
});
