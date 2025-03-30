import React, { useState, useEffect, useCallback, useMemo, useReducer } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import {
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from '@tanstack/react-table';

function CourseSearch() {
    const rerender = useReducer(() => ({}), {})[1];

    const columns = useMemo(
        () => [
            {
                accessorKey: 'g_course',
                header: () => 'Course',
                cell: info => info.getValue(),
                footer: props => props.column.id,
            },
            {
                accessorFn: row => row.g_city,
                id: 'g_city',
                cell: info => info.getValue(),
                header: () => <span>City</span>,
                footer: props => props.column.id,
            },
            {
                accessorKey: 'g_state',
                header: () => 'State',
                footer: props => props.column.id,
            },
            {
                accessorKey: 'g_country',
                header: () => <span>Country</span>,
                footer: props => props.column.id,
            },
            {
                accessorKey: 'id',
                header: () => 'ID',
                cell: info => info.getValue(),
                footer: props => props.column.id,
                enableColumnFilter: false,
            },
            {
                accessorKey: 'id',
                header: () => <span style={{ padding: '0 10px' }}>Link to Add</span>,
                cell: info => (
                    <Link to={`/add_course_by_id/${info.getValue()}`} style={{ padding: '0 10px' }}>
                        {"Add Course"}
                    </Link>
                ),
                footer: props => props.column.id,
                enableColumnFilter: false, // Disable filtering for this column
            },
        ],
        []
    );

    const [courseData, setCourseData] = useState([]);

    const refreshData = useCallback(async () => {
        try {
            const response = await axios.get('http://127.0.0.1:8005/readall', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
            });
            response.data.shift();
            setCourseData(response.data);
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }, []);

    useEffect(() => {
        refreshData();
    }, [refreshData]);

    return (
        <>
            <MyTable
                data={courseData}
                columns={columns}
            />
            <hr />
            <div>
                <button onClick={() => rerender()}>Force Rerender</button>
            </div>
            <div>
                <button onClick={() => refreshData()}>Refresh Data</button>
            </div>
        </>
    );
}

function MyTable({ data, columns }) {
    const [pagination, setPagination] = useState({
        pageIndex: 0,
        pageSize: 10,
    });

    const table = useReactTable({
        columns,
        data,
        debugTable: true,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onPaginationChange: setPagination,
        state: {
            pagination,
        },
    });

    return (
        <div className="p-2">
            <div className="h-2" />
            <table>
                <thead>
                {table.getHeaderGroups().map(headerGroup => (
                    <tr key={headerGroup.id}>
                        {headerGroup.headers.map(header => (
                            <th key={header.id} colSpan={header.colSpan}>
                                <div
                                    className={header.column.getCanSort() ? 'cursor-pointer select-none' : ''}
                                    onClick={header.column.getToggleSortingHandler()}
                                >
                                    {flexRender(
                                        header.column.columnDef.header,
                                        header.getContext()
                                    )}
                                    {{
                                        asc: ' 🔼',
                                        desc: ' 🔽',
                                    }[header.column.getIsSorted()] ?? null}
                                    {header.column.getCanFilter() ? (
                                        <div>
                                            <Filter column={header.column} table={table} />
                                        </div>
                                    ) : null}
                                </div>
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
                                {flexRender(
                                    cell.column.columnDef.cell,
                                    cell.getContext()
                                )}
                            </td>
                        ))}
                    </tr>
                ))}
                </tbody>
            </table>
            <div className="h-2" />
            <div className="flex items-center gap-2">
                <button
                    className="border rounded p-1"
                    onClick={() => table.firstPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    {'<<'}
                </button>
                <button
                    className="border rounded p-1"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    {'<'}
                </button>
                <button
                    className="border rounded p-1"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                >
                    {'>'}
                </button>
                <button
                    className="border rounded p-1"
                    onClick={() => table.lastPage()}
                    disabled={!table.getCanNextPage()}
                >
                    {'>>'}
                </button>
                <span className="flex items-center gap-1">
                    <div>Page</div>
                    <strong>
                        {table.getState().pagination.pageIndex + 1} of{' '}
                        {table.getPageCount().toLocaleString()}
                    </strong>
                </span>
                <span className="flex items-center gap-1">
                    | Go to page:
                    <input
                        type="number"
                        min="1"
                        max={table.getPageCount()}
                        defaultValue={table.getState().pagination.pageIndex + 1}
                        onChange={e => {
                            const page = e.target.value ? Number(e.target.value) - 1 : 0;
                            table.setPageIndex(page);
                        }}
                        className="border p-1 rounded w-16"
                    />
                </span>
                <select
                    value={table.getState().pagination.pageSize}
                    onChange={e => {
                        table.setPageSize(Number(e.target.value));
                    }}
                >
                    {[10, 20, 30, 40, 50].map(pageSize => (
                        <option key={pageSize} value={pageSize}>
                            Show {pageSize}
                        </option>
                    ))}
                </select>
            </div>
            <div>
                Showing {table.getRowModel().rows.length.toLocaleString()} of{' '}
                {table.getRowCount().toLocaleString()} Rows
            </div>
            <pre>{JSON.stringify(table.getState().pagination, null, 2)}</pre>
        </div>
    );
}

function Filter({ column, table }) {
    const firstValue = table
        .getPreFilteredRowModel()
        .flatRows[0]?.getValue(column.id);

    const columnFilterValue = column.getFilterValue();

    return typeof firstValue === 'number' ? (
        <div className="flex space-x-2" onClick={e => e.stopPropagation()}>
            <input
                type="number"
                value={(columnFilterValue ?? [])[0] ?? ''}
                onChange={e =>
                    column.setFilterValue((old = []) => [
                        e.target.value,
                        old[1],
                    ])
                }
                placeholder={`Min`}
                className="w-24 border shadow rounded"
            />
            <input
                type="number"
                value={(columnFilterValue ?? [])[1] ?? ''}
                onChange={e =>
                    column.setFilterValue((old = []) => [
                        old[0],
                        e.target.value,
                    ])
                }
                placeholder={`Max`}
                className="w-24 border shadow rounded"
            />
        </div>
    ) : (
        <input
            className="w-36 border shadow rounded"
            onChange={e => column.setFilterValue(e.target.value)}
            onClick={e => e.stopPropagation()}
            placeholder={`Search...`}
            type="text"
            value={columnFilterValue ?? ''}
        />
    );
}

export default CourseSearch;