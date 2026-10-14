import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import AdminEditCourseInfo from './AdminEditCourseInfo';

vi.mock('../services/api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));

const legacyCourse = {
    id: 7,
    display_name: 'Legacy Club',
    club_name: 'Legacy Club',
    course_name: '',
    address: '',
    city: 'Tampa',
    state: 'Florida',
    country: 'United States',
};

async function loadCourse(user) {
    render(<AdminEditCourseInfo />);
    await user.type(screen.getByPlaceholderText('Enter course ID'), '7');
    await user.click(screen.getByRole('button', { name: 'Load Course' }));
    await screen.findByRole('button', { name: 'Save Changes' });
}

describe('AdminEditCourseInfo country/state validation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.get.mockResolvedValue({ data: legacyCourse });
        api.put.mockImplementation((_, body) => Promise.resolve({ data: { ...legacyCourse, ...body } }));
    });

    it('blocks saving non-standard country and state values', async () => {
        const user = userEvent.setup();
        await loadCourse(user);

        expect(screen.getByRole('option', { name: 'United States (not a valid code)' })).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Save Changes' }));

        expect(api.put).not.toHaveBeenCalled();
        expect(screen.getByText('Fix the country/state codes before saving.')).toBeInTheDocument();
        expect(screen.getByText(/is not an ISO 3-letter country code/)).toBeInTheDocument();
        expect(screen.getByText(/Use the ISO subdivision code/)).toBeInTheDocument();
    });

    it('saves once the country is picked from the list and the state is a code', async () => {
        const user = userEvent.setup();
        await loadCourse(user);

        await user.selectOptions(screen.getByRole('combobox', { name: 'Country' }), 'USA');
        const state = screen.getByDisplayValue('Florida');
        await user.clear(state);
        await user.type(state, 'fl');
        await user.click(screen.getByRole('button', { name: 'Save Changes' }));

        expect(api.put).toHaveBeenCalledWith('/admin/courses/7/info', expect.objectContaining({ country: 'USA', state: 'FL' }));
        expect(await screen.findByText('Course information updated successfully.')).toBeInTheDocument();
    });
});
