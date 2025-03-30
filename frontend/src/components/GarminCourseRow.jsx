import React from 'react';

function GarminCourseRow(props) {
    function handleClick() {
        props.onDelete(props.id);
    }

    return (
        <tr className="course-row">
            <td>{props.g_course}</td>
            <td>{props.g_city}</td>
            <td>{props.g_state}</td>
            <td>{props.g_country}</td>
            <td>
                <button onClick={handleClick}>DELETE</button>
            </td>
        </tr>
    );
}

export default GarminCourseRow; 