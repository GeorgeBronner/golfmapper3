import { render, screen, waitFor } from '@testing-library/react';
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

const states = [
    { state: 'FL', country: 'USA', count: 2 },
    { state: 'GA', country: 'USA', count: 1 },
];

describe('AdminCourseMap', () => {
    beforeEach(() => {
        api.get.mockReset();
        api.get.mockImplementation(url => {
            if (url === '/admin/courses/states') return Promise.resolve({ data: states });
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

    it('fetches points for the chosen state and renders them', async () => {
        render(<AdminCourseMap />);
        const select = screen.getByRole('combobox', { name: 'State' });
        await screen.findByRole('option', { name: /FL, USA \(2\)/ });

        await userEvent.selectOptions(select, screen.getByRole('option', { name: /FL, USA/ }));

        await waitFor(() =>
            expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: { state: 'FL', country: 'USA' } })
        );
        expect(await screen.findByText('Tampa Club')).toBeInTheDocument();
        expect(screen.getByText('2 courses')).toBeInTheDocument();
    });

    it('requests every course for the All option', async () => {
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: /All courses \(3\)/ });
        await userEvent.selectOptions(screen.getByRole('combobox', { name: 'State' }), screen.getByRole('option', { name: /All courses/ }));
        await waitFor(() => expect(api.get).toHaveBeenCalledWith('/admin/courses/points', { params: {} }));
    });

    it('shows an error when the points request fails', async () => {
        api.get.mockImplementation(url =>
            url === '/admin/courses/states' ? Promise.resolve({ data: states }) : Promise.reject(new Error('boom'))
        );
        render(<AdminCourseMap />);
        await screen.findByRole('option', { name: /GA, USA/ });
        await userEvent.selectOptions(screen.getByRole('combobox', { name: 'State' }), screen.getByRole('option', { name: /GA, USA/ }));
        expect(await screen.findByText(/Failed to load courses/)).toBeInTheDocument();
    });
});
