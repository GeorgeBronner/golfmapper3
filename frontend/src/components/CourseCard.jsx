import React from 'react';

function CourseCard(props) {
    function handleClick() {
        props.onDelete(props.id);
    }

    return (
        <div className={"courseCard"}>
            <h1>{props.g_course}</h1>
            <div className="info-container">
                <p>{props.g_city}</p>
                <p>{props.year}</p>
            </div>
            <button onClick={handleClick}>DELETE</button>
        </div>);
}

export default CourseCard;