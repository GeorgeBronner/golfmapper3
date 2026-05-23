import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import CourseCard from './CourseCard';

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

    useEffect(() => { fetchCourses(); }, [fetchCourses]);

    const deleteUserCourse = (id) => {
        api.delete(`/user_courses/delete/${id}`)
            .then(() => fetchCourses())
            .catch(error => console.error(error));
    };

    const updateYear = (userCourseId, year) => {
        api.patch(`/user_courses/${userCourseId}/year`, { year })
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

    const uniqueYears = [...new Set(courses.map(c => c.year).filter(Boolean))];
    const latestYear = uniqueYears.length ? Math.max(...uniqueYears) : '—';

    if (loading) return <p className="loading-text">Loading courses…</p>;

    return (
        <div>
            <div className="page-header">
                <div>
                    <div className="page-title">My Courses</div>
                    <div className="page-subtitle">{courses.length} course{courses.length !== 1 ? 's' : ''} tracked</div>
                </div>
                <Link to="/course_search" className="btn-primary">＋ Add Course</Link>
            </div>

            <div className="stat-row">
                <div className="stat-chip">
                    <div className="stat-value">{courses.length}</div>
                    <div className="stat-label">Courses Played</div>
                </div>
                <div className="stat-chip">
                    <div className="stat-value">{uniqueYears.length}</div>
                    <div className="stat-label">Years Active</div>
                </div>
                <div className="stat-chip">
                    <div className="stat-value">{latestYear}</div>
                    <div className="stat-label">Most Recent</div>
                </div>
            </div>

            {courses.length === 0 ? (
                <div className="empty-state">
                    No courses yet —{' '}
                    <Link to="/course_search" style={{ color: 'var(--primary)', fontWeight: 500 }}>
                        search for your first one
                    </Link>
                </div>
            ) : (
                <div className="table-card">
                    <div className="table-card-header">
                        <span className="table-card-title">Course History</span>
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                        <table className="fairway-table">
                            <thead>
                                <tr>
                                    <th
                                        onClick={() => sortData('display_name')}
                                        tabIndex={0}
                                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && sortData('display_name')}
                                    >
                                        Course Name {sortConfig.key === 'display_name' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↕'}
                                    </th>
                                    <th
                                        onClick={() => sortData('city')}
                                        tabIndex={0}
                                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && sortData('city')}
                                    >
                                        Location {sortConfig.key === 'city' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↕'}
                                    </th>
                                    <th
                                        onClick={() => sortData('year')}
                                        tabIndex={0}
                                        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && sortData('year')}
                                    >
                                        Year {sortConfig.key === 'year' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↕'}
                                    </th>
                                    <th style={{ width: '48px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedCourses.map(course => (
                                    <CourseCard
                                        key={course.user_course_id}
                                        id={course.id}
                                        user_course_id={course.user_course_id}
                                        display_name={course.display_name}
                                        city={course.city}
                                        year={course.year}
                                        onDelete={() => deleteUserCourse(course.id)}
                                        onYearSave={(year) => updateYear(course.user_course_id, year)}
                                    />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CourseList;
