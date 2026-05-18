import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
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

    useEffect(() => { fetchCourses(); }, [fetchCourses]);

    const columns = useMemo(() => [
        { accessorKey: 'display_name', header: 'Course Name' },
        { accessorKey: 'city', header: 'City' },
        { accessorKey: 'state', header: 'State' },
        { accessorKey: 'country', header: 'Country' },
        {
            id: 'add_link',
            accessorKey: 'id',
            header: 'Add',
            cell: ({ row }) => (
                <Link to={`/add_course_by_id/${row.original.id}`} className="btn-primary" style={{ padding: '5px 10px', fontSize: '12px' }}>
                    Add
                </Link>
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

    if (loading) return <p className="loading-text">Loading courses…</p>;

    const filtered = table.getFilteredRowModel().rows.length;

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">All Courses</div>
                    <div className="page-subtitle">Browse the full Garmin course database</div>
                </div>
            </div>

            <div className="table-card">
                <div className="table-card-header">
                    <span className="table-card-title">{filtered.toLocaleString()} courses</span>
                    <input
                        className="filter-input"
                        value={globalFilter ?? ''}
                        onChange={e => setGlobalFilter(e.target.value)}
                        placeholder="🔍 Search courses…"
                        style={{ width: '220px' }}
                    />
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table className="fairway-table">
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
                </div>

                <div className="pagination-row">
                    <button className="pagination-btn" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>‹ Prev</button>
                    <span className="pagination-info">
                        Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
                    </span>
                    <button className="pagination-btn" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next ›</button>
                    <span className="pagination-count">{filtered.toLocaleString()} results</span>
                </div>
            </div>
        </div>
    );
}

export default GarminCourses;
