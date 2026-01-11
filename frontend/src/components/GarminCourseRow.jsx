import React from 'react';

function GarminCourseRow(props) {
    function handleClick() {
        props.onDelete(props.id);
    }

    return (
        <tr className="course-row">
            <td>{props.display_name}</td>
            <td>{props.city}</td>
            <td>{props.state}</td>
            <td>{props.country}</td>
            <td>
                <button onClick={handleClick}>DELETE</button>
            </td>
        </tr>
    );
}

export default GarminCourseRow; 