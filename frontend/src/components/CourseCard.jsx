import React, { useState, useRef, useEffect } from 'react';

function CourseCard({ id, display_name, city, state, country, year, onDelete, onYearSave }) {
    const [editing, setEditing] = useState(false);
    const [draftYear, setDraftYear] = useState('');
    const inputRef = useRef(null);

    useEffect(() => {
        if (editing) inputRef.current?.focus();
    }, [editing]);

    function startEdit() {
        setDraftYear(year ?? '');
        setEditing(true);
    }

    function commitEdit() {
        const parsed = parseInt(draftYear, 10);
        if (!isNaN(parsed) && parsed >= 1900 && parsed <= 2070 && parsed !== year) {
            onYearSave(parsed);
        }
        setEditing(false);
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') commitEdit();
        if (e.key === 'Escape') setEditing(false);
    }

    function handleDelete() {
        if (!window.confirm(`Delete "${display_name}"?`)) return;
        onDelete(id);
    }

    return (
        <tr>
            <td className="td-course-name">{display_name}</td>
            <td className="td-location">{city}</td>
            <td>{state}</td>
            <td>{country}</td>
            <td
                className="td-year"
                onClick={editing ? undefined : startEdit}
                title={editing ? undefined : 'Click to edit year'}
                style={editing ? undefined : { cursor: 'pointer' }}
            >
                {editing ? (
                    <input
                        ref={inputRef}
                        type="number"
                        value={draftYear}
                        onChange={e => setDraftYear(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={handleKeyDown}
                        style={{ width: '72px', padding: '2px 6px', fontSize: 'inherit', borderRadius: '4px', border: '1px solid var(--primary)' }}
                        min="1900"
                        max="2070"
                    />
                ) : (
                    <span style={{ borderBottom: '1px dashed var(--text-muted)', paddingBottom: '1px' }}>
                        {year ?? '—'}
                    </span>
                )}
            </td>
            <td>
                <button
                    type="button"
                    className="btn-delete-icon"
                    onClick={handleDelete}
                    aria-label={`Delete ${display_name}`}
                    title={`Delete ${display_name}`}
                >
                    🗑
                </button>
            </td>
        </tr>
    );
}

export default CourseCard;
