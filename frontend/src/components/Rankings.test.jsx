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

    it('shows a tied rank as printed', async () => {
        api.get.mockImplementation(url => Promise.resolve({
            data: url === '/rankings' ? lists : {
                label: '2025-26',
                entries: [{ rank: 54, rank_label: 'T53', prior_rank: 'N', course_id: 10, name: 'St Georges Hill', published_name: 'St George', city: 'Weybridge', state: 'SRY', played: false }],
            },
        }));
        render(<Rankings />);
        expect(await screen.findByText('T53')).toBeInTheDocument();
        expect(screen.queryByText('54')).not.toBeInTheDocument();
    });

    it('shows the country, not a regional code, for a course outside the US', async () => {
        api.get.mockImplementation(url => Promise.resolve({
            data: url === '/rankings' ? lists : {
                label: '2025-26',
                entries: [{ rank: 10, prior_rank: '9', course_id: 10, name: 'Ballybunion', published_name: 'Ballybunion', city: 'Ballybunion', state: 'KY', country: 'IRL', played: false }],
            },
        }));
        render(<Rankings />);
        expect(await screen.findByText('Ireland')).toBeInTheDocument();
        expect(screen.queryByText('KY')).not.toBeInTheDocument();
    });

    it('groups the state lists under one Best in State choice with a state picker', async () => {
        const withStates = [
            { ...lists[0], scope: 'us-public' },
            { id: 3, name: 'Best Courses in Texas', publisher: 'Golf Digest', scope: 'us-state-TX', editions: [{ id: 31, label: '2025-26' }] },
            { id: 4, name: 'Best Courses in Alabama', publisher: 'Golf Digest', scope: 'us-state-AL', editions: [{ id: 41, label: '2025-26' }] },
        ];
        api.get.mockImplementation(url => Promise.resolve({
            data: url === '/rankings' ? withStates : {
                label: '2025-26',
                entries: [{ rank: 1, prior_rank: null, access: 'private', course_id: 10, name: 'Colonial', published_name: 'Colonial', city: 'Fort Worth', state: 'TX', played: false }],
            },
        }));
        render(<Rankings />);
        await screen.findByText('Colonial');  // starts on the first list
        const group = screen.getByLabelText('Ranking list');
        expect([...group.querySelectorAll('option')].map(o => o.textContent)).toEqual(['Top 100 Public', 'Best in State']);
        expect(screen.queryByLabelText('State')).not.toBeInTheDocument();

        fireEvent.change(group, { target: { value: 'states' } });
        const state = await screen.findByLabelText('State');
        expect([...state.querySelectorAll('option')].map(o => o.textContent)).toEqual(['Alabama', 'Texas']);
        expect(api.get).toHaveBeenCalledWith('/rankings/editions/41');  // alphabetical: Alabama first
        expect(screen.getByText('private')).toBeInTheDocument();  // the Access column appears

        fireEvent.change(state, { target: { value: '3' } });
        await screen.findByText('Colonial');
        expect(api.get).toHaveBeenCalledWith('/rankings/editions/31');
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
