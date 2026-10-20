import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import AdminCourseMap from './AdminCourseMap';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));
// Leaflet rendering isn't under test here; just capture what's passed in.
vi.mock('./CourseMap', () => ({
    default: ({ groups }) => (
        <ul data-testid="course-map">
            {groups[0].points.map(p => <li key={p.id}>{p.name}</li>)}
        </ul>
    ),
}));

const regions = {
    us_states: [
        { state: 'FL', count: 2 },
        { state: 'GA', count: 1 },
    ],
    countries: [
        { country: 'CAN', count: 1747 },
        { country: 'USA', count: 3 },
        { country: null, count: 4 },
    ],
};

const pick = async name =>
    userEvent.selectOptions(screen.getByRole('combobox', { name: 'Region' }), screen.getByRole('option', { name }));

describe('AdminCourseMap', () => {
    beforeEach(() => {
        api.get.mockReset();
        api.get.mockImplementation(url => {
            if (url === '/admin/courses/regions') return Promise.resolve({ data: regions });
            if (url === '/admin/courses/points') {
                return Promise.resolve({
                    data: {
                        fields: ['id', 'lat', 'lon', 'name'],
                        points: [[1, 27.95, -82.46, 'Tampa Club'], [2, 25.76, -80.19, 'Miami Club']],
                    },
                });
            }
            return Promise.reject(new Error(`unexpected ${url}`));
        });
    });

    it('lists US states first, then countries', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'FL (2)' });
        const [us, countries] = screen.getAllByRole('group');
        expect(us).toHaveAttribute('label', 'United States');
        expect(within(us).getAllByRole('option').map(o => o.textContent)).toEqual(['FL (2)', 'GA (1)']);
        expect(countries).toHaveAttribute('label', 'Countries');
        expect(within(countries).getAllByRole('option').map(o => o.textContent)).toEqual([
            'CAN (1,747)',
            'USA (3)',
            'No country (4)',
        ]);
    });

    it('fetches a US state and renders its courses', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'FL (2)' });
        await pick('FL (2)');
        await waitFor(() =>
            expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: { state: 'FL', country: 'USA' } })
        );
        expect(await screen.findByText('Tampa Club')).toBeInTheDocument();
        expect(screen.getByText('2 courses')).toBeInTheDocument();
    });

    it('fetches a whole country', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'CAN (1,747)' });
        await pick('CAN (1,747)');
        await waitFor(() =>
            expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: { country: 'CAN' } })
        );
    });

    it('sends an empty country for courses with no country', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'No country (4)' });
        await pick('No country (4)');
        await waitFor(() =>
            expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: { country: '' } })
        );
    });

    it('requests every course for the All option', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'FL (2)' });
        await pick(/All courses/);
        await waitFor(() => expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: {} }));
    });

    it('shows an error when the points request fails', async () => {
        api.get.mockImplementation(url =>
            url === '/admin/courses/regions' ? Promise.resolve({ data: regions }) : Promise.reject(new Error('boom'))
        );
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: 'GA (1)' });
        await pick('GA (1)');
        expect(await screen.findByText(/Failed to load courses/)).toBeInTheDocument();
    });
});
