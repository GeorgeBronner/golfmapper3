import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import Rankings from './Rankings';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));

const lists = [{
    id: 1, name: 'Top 100 Public', publisher: 'Golf Digest',
    editions: [{ id: 2, label: '2025-26' }, { id: 1, label: '2023-24' }],
}];
const edition = (label, played) => ({
    label,
    entries: [
        { rank: 1, prior_rank: '1', course_id: 10, name: 'Pebble Beach', published_name: 'Pebble Beach', city: 'Pebble Beach', state: 'CA', played },
        { rank: 2, prior_rank: null, course_id: 11, name: 'Erin Hills', published_name: 'Erin Hills', city: 'Erin', state: 'WI', played: false },
    ],
});

describe('Rankings', () => {
    beforeEach(() => {
        api.get.mockReset();
        api.get.mockImplementation(url => Promise.resolve({
            data: url === '/rankings' ? lists : url.endsWith('/2') ? edition('2025-26', true) : edition('2023-24', false),
        }));
    });

    it('shows the newest edition and how many courses the user has played', async () => {
        render(<Rankings />);
        expect(await screen.findByText('1 / 2')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/rankings/editions/2');
    });

    it('loads another edition when selected', async () => {
        render(<Rankings />);
        await screen.findByText('1 / 2');
        fireEvent.change(screen.getByLabelText('Edition'), { target: { value: '1' } });
        expect(await screen.findByText('0 / 2')).toBeInTheDocument();
    });

    it('clears the table when switching to a list with no editions', async () => {
        const two = [...lists, { id: 2, name: 'Empty List', publisher: 'Golf Digest', editions: [] }];
        api.get.mockImplementation(url => Promise.resolve({
            data: url === '/rankings' ? two : edition('2025-26', true),
        }));
        render(<Rankings />);
        await screen.findByText('1 / 2');
        fireEvent.change(screen.getByLabelText('Ranking list'), { target: { value: '2' } });
        expect(screen.queryByText('1 / 2')).not.toBeInTheDocument();
        expect(screen.queryByText('Pebble Beach')).not.toBeInTheDocument();
    });
});
