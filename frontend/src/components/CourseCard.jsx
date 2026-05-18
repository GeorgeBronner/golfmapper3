import React from 'react';

function CourseCard({ id, display_name, city, year, onDelete }) {
    function handleClick() {
        if (!window.confirm(`Delete "${display_name}"?`)) return;
        onDelete(id);
    }

    return (
        <tr>
            <td className="td-course-name">{display_name}</td>
            <td className="td-location">{city}</td>
            <td className="td-year">{year}</td>
            <td>
                <button
                    type="button"
                    className="btn-delete-icon"
                    onClick={handleClick}
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
