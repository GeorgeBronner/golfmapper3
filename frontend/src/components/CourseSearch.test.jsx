import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import CourseSearch from './CourseSearch';

vi.mock('../services/api', () => ({ default: { get: vi.fn() } }));

// 12 courses so the default page size (10) yields two pages.
const courses = Array.from({ length: 12 }, (_, i) => ({
    id: i + 1,
    display_name: `Course ${String.fromCharCode(65 + i)}`,
    city: i % 2 === 0 ? 'Mobile' : 'Austin',
    state: i % 2 === 0 ? 'Alabama' : 'Texas',
    country: 'US',
}));

function bodyRows() {
    const [, tbody] = screen.getAllByRole('rowgroup');
    return within(tbody).getAllByRole('row');
}

function firstCellTexts() {
    return bodyRows().map(row => within(row).getAllByRole('cell')[0].textContent);
}

async function renderSearch() {
    render(
        <MemoryRouter>
            <CourseSearch />
        </MemoryRouter>
    );
    await screen.findByText('Course Search');
}

describe('CourseSearch', () => {
    beforeEach(() => {
        api.get.mockResolvedValue({ data: courses });
    });

    it('paginates the course list', async () => {
        const user = userEvent.setup();
        await renderSearch();

        expect(bodyRows()).toHaveLength(10);
        expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument();

        await user.click(screen.getByRole('button', { name: '›' }));
        expect(bodyRows()).toHaveLength(2);
        expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument();

        await user.selectOptions(screen.getByRole('combobox'), '20');
        expect(bodyRows()).toHaveLength(12);
    });

    it('filters by a column value', async () => {
        const user = userEvent.setup();
        await renderSearch();

        const [, cityFilter] = screen.getAllByPlaceholderText('Filter…');
        await user.type(cityFilter, 'aus');

        expect(bodyRows()).toHaveLength(6);
        expect(screen.getByText(/^6 of 12 courses/)).toBeInTheDocument();
    });

    it('sorts when a header is clicked', async () => {
        const user = userEvent.setup();
        await renderSearch();

        await user.click(screen.getByRole('columnheader', { name: /^Course/ }));
        expect(firstCellTexts()[0]).toBe('Course A');

        await user.click(screen.getByRole('columnheader', { name: /^Course/ }));
        expect(firstCellTexts()[0]).toBe('Course L');
    });
});
