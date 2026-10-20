import { render, screen } from '@testing-library/react';
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
        expect(screen.queryByTestId('course-map')).toBeNull();
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

    it('shows an error when loading fails', async () => {
        api.get.mockImplementation(() => Promise.reject(new Error('boom')));
        render(<AllUsersMap />);
        expect(await screen.findByText(/Failed to load map/)).toBeInTheDocument();
    });
});
