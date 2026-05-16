import React, { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../services/api';
import {
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    useReactTable,
} from '@tanstack/react-table';

function GarminCourses() {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [globalFilter, setGlobalFilter] = useState('');

    const fetchCourses = useCallback(() => {
        setLoading(true);
        api.get('/garmin_courses/readall')
            .then(res => setCourses(res.data))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchCourses();
    }, [fetchCourses]);

    const deleteUserCourse = (id) => {
        api.delete(`/user_courses/delete/${id}`)
            .then(() => fetchCourses())
            .catch(error => console.error(error));
    };

    const columns = useMemo(() => [
        { accessorKey: 'display_name', header: 'Course Name' },
        { accessorKey: 'city', header: 'City' },
        { accessorKey: 'state', header: 'State' },
        { accessorKey: 'country', header: 'Country' },
        {
            id: 'actions',
            header: 'Actions',
            cell: ({ row }) => (
                <button onClick={() => deleteUserCourse(row.original.id)}>Delete</button>
            ),
            enableGlobalFilter: false,
        },
    ], []);

    const table = useReactTable({
        data: courses,
        columns,
        state: { globalFilter },
        onGlobalFilterChange: setGlobalFilter,
        getCoreRowModel: getCoreRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        initialState: { pagination: { pageSize: 20 } },
    });

    if (loading) return <p>Loading courses...</p>;

    return (
        <div className="course-list-container">
            <div style={{ marginBottom: '0.5rem' }}>
                <input
                    value={globalFilter ?? ''}
                    onChange={e => setGlobalFilter(e.target.value)}
                    placeholder="Search courses..."
                    style={{ padding: '0.4rem', width: '300px' }}
                />
            </div>
            <table className="course-table">
                <thead>
                    {table.getHeaderGroups().map(hg => (
                        <tr key={hg.id}>
                            {hg.headers.map(header => (
                                <th key={header.id}>
                                    {flexRender(header.column.columnDef.header, header.getContext())}
                                </th>
                            ))}
                        </tr>
                    ))}
                </thead>
                <tbody>
                    {table.getRowModel().rows.map(row => (
                        <tr key={row.id}>
                            {row.getVisibleCells().map(cell => (
                                <td key={cell.id}>
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
            <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>{'<'}</button>
                <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
                <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>{'>'}</button>
                <span style={{ marginLeft: '1rem' }}>
                    {table.getFilteredRowModel().rows.length.toLocaleString()} courses
                </span>
            </div>
        </div>
    );
}

export default GarminCourses;
