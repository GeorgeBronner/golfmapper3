import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import {
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from '@tanstack/react-table';

function CourseSearch() {
    const columns = useMemo(() => [
        {
            accessorKey: 'display_name',
            header: 'Course',
            cell: info => info.getValue(),
        },
        {
            accessorFn: row => row.city,
            id: 'city',
            header: 'City',
            cell: info => info.getValue(),
        },
        {
            accessorKey: 'state',
            header: 'State',
        },
        {
            accessorKey: 'country',
            header: 'Country',
        },
        {
            accessorKey: 'id',
            header: 'ID',
            enableColumnFilter: false,
        },
        {
            id: 'add_link',
            accessorKey: 'id',
            header: 'Add',
            cell: info => (
                <Link to={`/add_course_by_id/${info.getValue()}`} className="btn-primary" style={{ padding: '5px 10px', fontSize: '12px' }}>
                    Add
                </Link>
            ),
            enableColumnFilter: false,
        },
    ], []);

    const [courseData, setCourseData] = useState([]);
    const [loading, setLoading] = useState(true);

    const refreshData = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.get('/garmin_courses/readall');
            setCourseData(response.data);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { refreshData(); }, [refreshData]);

    if (loading) return <p className="loading-text">Loading courses…</p>;

    return (
        <div className="course-search">
            <div className="page-header">
                <div>
                    <div className="page-title">Course Search</div>
                    <div className="page-subtitle">Filter by any column to find a course</div>
                </div>
                <button className="btn-ghost" onClick={refreshData}>⟳ Refresh</button>
            </div>

            <SearchTable data={courseData} columns={columns} />
        </div>
    );
}

function SearchTable({ data, columns }) {
    const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 });

    const table = useReactTable({
        columns,
        data,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onPaginationChange: setPagination,
        state: { pagination },
    });

    return (
        <div className="table-card">
            <div className="table-card-header">
                <span className="table-card-title">
                    {table.getFilteredRowModel().rows.length.toLocaleString()} of {table.getRowCount().toLocaleString()} courses
                </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table className="fairway-table">
                    <thead>
                        {table.getHeaderGroups().map(headerGroup => (
                            <tr key={headerGroup.id}>
                                {headerGroup.headers.map(header => (
                                    <th
                                        key={header.id}
                                        colSpan={header.colSpan}
                                        onClick={header.column.getToggleSortingHandler()}
                                        tabIndex={header.column.getCanSort() ? 0 : undefined}
                                        onKeyDown={e => {
                                            if ((e.key === 'Enter' || e.key === ' ') && header.column.getCanSort())
                                                header.column.getToggleSortingHandler()(e);
                                        }}
                                        style={{ cursor: header.column.getCanSort() ? 'pointer' : 'default' }}
                                    >
                                        {flexRender(header.column.columnDef.header, header.getContext())}
                                        {{ asc: ' ↑', desc: ' ↓' }[header.column.getIsSorted()] ?? null}
                                        {header.column.getCanFilter() && (
                                            <div onClick={e => e.stopPropagation()} style={{ marginTop: '4px' }}>
                                                <ColumnFilter column={header.column} />
                                            </div>
                                        )}
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
                <button className="pagination-btn" onClick={() => table.firstPage()} disabled={!table.getCanPreviousPage()}>«</button>
                <button className="pagination-btn" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>‹</button>
                <span className="pagination-info">
                    Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount().toLocaleString()}
                </span>
                <button className="pagination-btn" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>›</button>
                <button className="pagination-btn" onClick={() => table.lastPage()} disabled={!table.getCanNextPage()}>»</button>
                <span className="pagination-count">{table.getRowCount().toLocaleString()} total</span>
                <select
                    value={table.getState().pagination.pageSize}
                    onChange={e => table.setPageSize(Number(e.target.value))}
                    className="filter-input"
                    style={{ marginLeft: 'auto', width: 'auto' }}
                >
                    {[10, 20, 50].map(size => (
                        <option key={size} value={size}>Show {size}</option>
                    ))}
                </select>
            </div>
        </div>
    );
}

function ColumnFilter({ column }) {
    const value = column.getFilterValue() ?? '';
    return (
        <input
            className="filter-input"
            value={value}
            onChange={e => column.setFilterValue(e.target.value)}
            placeholder="Filter…"
            style={{ width: '100%' }}
        />
    );
}

export default CourseSearch;
