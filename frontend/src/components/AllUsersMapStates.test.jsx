import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import AllUsersMap from './AllUsersMap';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));
vi.mock('./AuthProvider', () => ({ useAuth: () => ({ token: 't' }) }));
// Every distinct focusPoints array the map was given: a new one makes the real map re-fit.
const focusSeen = vi.hoisted(() => new Set());
vi.mock('./CourseMap', () => ({
    default: ({ groups, focusPoints }) => (
        <div data-testid="course-map" data-focus={focusPoints ? String(focusPoints.length) : ''} ref={() => { if (focusPoints) focusSeen.add(focusPoints); }}>
            {groups.map(g => (
                <section key={g.name} data-color={g.color}>
                    {g.name}: {g.points.map(p => `${p.name} (${p.year})`).join(', ')}
                </section>
            ))}
        </div>
    ),
}));

const fields = ['id', 'lat', 'lon', 'name', 'year'];
const rankFields = [...fields, 'rank', 'rank_label', 'access'];
const lists = [
    { id: 7, name: 'US Public', publisher: 'Golf Digest', scope: 'us-public', editions: [{ id: 71, label: '2025-26' }] },
    // Out of alphabetical order on purpose: the picker sorts them.
    {
        id: 21, name: 'Best Courses in Texas', publisher: 'Golf Digest', scope: 'us-state-TX',
        editions: [{ id: 211, label: '2025-26' }, { id: 210, label: '2023-24' }],
    },
    {
        id: 20, name: 'Best Courses in Alabama', publisher: 'Golf Digest', scope: 'us-state-AL',
        editions: [{ id: 201, label: '2025-26' }, { id: 200, label: '2023-24' }],
    },
];
const allStates = [
    [5, 31, -87, 'Grand', 2025, 1, null, 'public', 'Best Courses in Alabama'],
    [6, 32, -97, 'Colonial', 2025, 2, 'T2', 'private', 'Best Courses in Texas'],
    [8, 33, -96, 'Resort', 2025, 3, null, null, 'Best Courses in Texas'],
];
const texas = [
    [6, 32, -97, 'Colonial', 2025, 2, 'T2', 'private'],
    [8, 33, -96, 'Resort', 2025, 3, null, null],
];

const mockApi = (url, config) => {
    if (url === '/map/all_points') return Promise.resolve({ data: { fields, users: [] } });
    if (url === '/rankings') return Promise.resolve({ data: lists });
    if (url === '/map/rankings/7/points') {
        return Promise.resolve({ data: { fields: rankFields, edition: '2025-26', points: [] } });
    }
    if (url === '/map/rankings/states/points') {
        return Promise.resolve({
            data: { fields: [...rankFields, 'list'], edition: config.params.edition, points: allStates },
        });
    }
    if (url === '/map/rankings/21/points') {
        return Promise.resolve({ data: { fields: rankFields, edition: '2025-26', points: texas } });
    }
    return Promise.reject(new Error(`unexpected ${url}`));
};

describe('AllUsersMap best in state', () => {
    beforeEach(() => {
        focusSeen.clear();
        api.get.mockReset();
        api.get.mockImplementation(mockApi);
    });

    it('offers one sorted Best in State control instead of a checkbox per state', async () => {
        render(<AllUsersMap />);
        const stateSelect = await screen.findByLabelText('Best in State state');
        const options = [...stateSelect.querySelectorAll('option')].map(o => o.textContent);
        expect(options).toEqual(['All states', 'Alabama', 'Texas']);
        expect(screen.queryByLabelText('Best Courses in Texas')).toBeNull();
        expect(api.get).not.toHaveBeenCalledWith('/map/rankings/states/points', expect.anything());
    });

    it('shows every state as one layer, and hides private clubs on request', async () => {
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByLabelText('Best in State state');
        await user.click(screen.getByLabelText('Best in State'));

        const group = await screen.findByText(/Best in State 2025-26: Grand \(2025\), Colonial \(2025\), Resort \(2025\)/);
        expect(group).toHaveAttribute('data-color', '#5f3dc4');
        expect(api.get).toHaveBeenCalledWith('/map/rankings/states/points', { params: { edition: '2025-26' } });
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-focus', '');

        await user.click(screen.getByLabelText('Public only'));
        expect(await screen.findByText(/Best in State 2025-26: Grand \(2025\), Resort \(2025\)$/)).toBeInTheDocument();
        // all_points, /rankings, the first list's layer and one states call: the filter is client-side.
        expect(api.get).toHaveBeenCalledTimes(4);
    });

    it("loads one state's list for the chosen edition and zooms to it", async () => {
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByLabelText('Best in State state');
        await user.selectOptions(screen.getByLabelText('Best in State state'), '21');
        await user.click(screen.getByLabelText('Best in State'));

        expect(await screen.findByText(/Best Courses in Texas 2025-26: Colonial/)).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/map/rankings/21/points', { params: { edition_id: 211 } });
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-focus', '2');

        await user.click(screen.getByLabelText('Public only'));
        await screen.findByText(/Best Courses in Texas 2025-26: Resort \(2025\)$/);
        expect(screen.getByTestId('course-map')).toHaveAttribute('data-focus', '1');
    });

    it('says so when the chosen state has no list for the chosen edition', async () => {
        const wyoming = {
            id: 22, name: 'Best Courses in Wyoming', publisher: 'Golf Digest', scope: 'us-state-WY',
            editions: [{ id: 221, label: '2025-26' }],  // no 2023-24
        };
        api.get.mockImplementation((url, config) => (
            url === '/rankings' ? Promise.resolve({ data: [...lists, wyoming] }) : mockApi(url, config)
        ));
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByLabelText('Best in State state');
        await user.selectOptions(screen.getByLabelText('Best in State state'), '22');
        await user.click(screen.getByLabelText('Show old years'));
        await user.selectOptions(screen.getByLabelText('Best in State edition'), '2023-24');
        await user.click(screen.getByLabelText('Best in State'));

        expect(await screen.findByRole('alert')).toHaveTextContent('no 2023-24 list for Wyoming');
        expect(api.get).not.toHaveBeenCalledWith('/map/rankings/22/points', expect.anything());
        expect(screen.queryByText(/Best Courses in Wyoming/, { selector: 'section' })).toBeNull();
    });

    it('does not re-zoom when another layer is toggled', async () => {
        const user = userEvent.setup();
        render(<AllUsersMap />);
        await screen.findByLabelText('Best in State state');
        await user.selectOptions(screen.getByLabelText('Best in State state'), '21');
        await user.click(screen.getByLabelText('Best in State'));
        await screen.findByText(/Best Courses in Texas 2025-26/);

        const before = focusSeen.size;
        await user.click(screen.getByLabelText('US Public'));
        await user.click(screen.getByLabelText('US Public'));
        expect(focusSeen.size).toBe(before);
    });
});
