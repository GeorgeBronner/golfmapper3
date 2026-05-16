import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import CourseCard from "./CourseCard";

function CourseList() {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortConfig, setSortConfig] = useState({ key: 'year', direction: 'desc' });

    const fetchCourses = useCallback(() => {
        setLoading(true);
        api.get('/user_courses/readall_ids_w_year')
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

    const sortData = (key) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
        }));
    };

    const sortedCourses = [...courses].sort((a, b) => {
        if (!sortConfig.key) return 0;
        if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
        if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });

    if (loading) return <p>Loading courses...</p>;

    return (
        <div className="course-list-container">
            <table className="course-table">
                <thead>
                    <tr>
                        <th onClick={() => sortData('display_name')} className="sortable">
                            Course Name {sortConfig.key === 'display_name' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </th>
                        <th onClick={() => sortData('city')} className="sortable">
                            City {sortConfig.key === 'city' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </th>
                        <th onClick={() => sortData('year')} className="sortable" data-sort={sortConfig.key === 'year' ? sortConfig.direction : null}>
                            Year {sortConfig.key === 'year' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                        </th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedCourses.map(course =>
                        <CourseCard
                            key={course.id}
                            id={course.id}
                            display_name={course.display_name}
                            city={course.city}
                            year={course.year}
                            onDelete={() => deleteUserCourse(course.id)}
                        />
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default CourseList;
