import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import GarminCourseRow from "./GarminCourseRow";

function GarminCourses() {
    const [courses, setCourses] = useState([]);

    const fetchCourses = useCallback(() => {
        api.get('/garmin_courses/readall')
            .then(res => setCourses(res.data));
    }, []);

    useEffect(() => {
        fetchCourses();
    }, [fetchCourses]);

    const deleteUserCourse = (id) => {
        api.delete(`/user_courses/delete/${id}`)
            .then(() => fetchCourses())
            .catch(error => console.error(error));
    };

    return (
        <div className="course-list-container">
            <table className="course-table">
                <thead>
                    <tr>
                        <th>Course Name</th>
                        <th>City</th>
                        <th>State</th>
                        <th>Country</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {courses.map(course =>
                        <GarminCourseRow
                            key={course.id}
                            id={course.id}
                            display_name={course.display_name}
                            city={course.city}
                            state={course.state}
                            country={course.country}
                            onDelete={() => deleteUserCourse(course.id)}
                        />
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default GarminCourses;
