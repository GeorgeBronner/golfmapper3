import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import Stats from './Stats';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));

const courses = [
    { id: 1, display_name: 'Pebble Beach', club_name: 'Pebble Beach', country: 'USA', state: 'CA', year: 2019 },
    { id: 2, display_name: 'Local Muni', club_name: 'Local Muni', country: 'USA', state: 'SC', year: null },
];
const progress = {
    list_id: 1, name: 'Top Public', size: 100, ever_listed: 165,
    current: { label: '2025-26', total: 100, played: 1, by_state: { CA: { ranked: 7, played: 1 }, WI: { ranked: 11, played: 0 } } },
    editions: [],
    courses: [{ course_id: 1, name: 'Pebble Beach - Pebble Beach Golf Links', state: 'CA', year: 2019, current_rank: 1, ranks: { '2025-26': 1 } }],
};

const mockApi = ({ rankings = true, user = courses } = {}) =>
    api.get.mockImplementation(async url => {
        if (url === '/user_courses/readall_ids_w_year') return { data: user };
        if (!rankings) throw new Error('no rankings');
        return { data: url === '/rankings' ? [{ id: 1 }] : progress };
    });

describe('Stats', () => {
    beforeEach(() => { api.get.mockReset(); });

    it('shows totals and Top 100 progress', async () => {
        mockApi();
        render(<Stats />);
        expect(await screen.findByText('Courses played')).toBeInTheDocument();
        expect(screen.getByText('2/50')).toBeInTheDocument();
        expect(screen.getByText('of 165 courses ever listed')).toBeInTheDocument();
        expect(screen.getByText('2025-26 edition')).toBeInTheDocument();
        expect(screen.getByText('HIGHEST RANKED PLAYED')).toBeInTheDocument();
        expect(screen.getByText('1 with no year set')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/rankings/lists/1/progress');
    });

    it('switches the map to the Top 100 layer', async () => {
        mockApi();
        render(<Stats />);
        fireEvent.click(await screen.findByRole('button', { name: 'Top 100' }));
        expect(screen.getByTitle('Wisconsin: 0 of 11 ranked courses played')).toBeInTheDocument();
        expect(screen.getByText(/Gold = Top 100/)).toBeInTheDocument();
    });

    it('still works when the rankings fail to load', async () => {
        mockApi({ rankings: false });
        render(<Stats />);
        expect(await screen.findByText('Courses played')).toBeInTheDocument();
        expect(screen.queryByText("On today's Top 100")).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Top 100' })).not.toBeInTheDocument();
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
