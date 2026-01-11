import React from 'react';
import axios from 'axios';
import CourseCard from "./CourseCard";
import { API_BASE_URL } from '../config';

export default class CourseList extends React.Component {
    state = {
        courses: [],
        sortConfig: {
            key: 'year',
            direction: 'desc'
        }
    }

    componentDidMount() {
        this.fetchCourses();
    }

    fetchCourses = () => {
        axios.get(`${API_BASE_URL}/user_courses/readall_ids_w_year`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }})
            .then(res => {
                const courses = res.data;
                this.setState({ courses });
            })
    }

    deleteUserCourse = (id) => {
        axios.delete(`${API_BASE_URL}/user_courses/delete/${id}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }})
            .then(response => {
                console.log(response);
                this.fetchCourses();
            })
            .catch(error => {
                console.error(error);
            });
    }

    sortData = (key) => {
        let direction = 'asc';
        if (this.state.sortConfig.key === key && this.state.sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        this.setState({ sortConfig: { key, direction } });
    }

    getSortedData = () => {
        const { courses, sortConfig } = this.state;
        if (!sortConfig.key) return courses;

        return [...courses].sort((a, b) => {
            if (a[sortConfig.key] < b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? -1 : 1;
            }
            if (a[sortConfig.key] > b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }

    render() {
        const { sortConfig } = this.state;
        const sortedCourses = this.getSortedData();

        return (
            <div className="course-list-container">
                <table className="course-table">
                    <thead>
                        <tr>
                            <th onClick={() => this.sortData('display_name')} className="sortable">
                                Course Name {sortConfig.key === 'display_name' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                            </th>
                            <th onClick={() => this.sortData('city')} className="sortable">
                                City {sortConfig.key === 'city' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                            </th>
                            <th onClick={() => this.sortData('year')} className="sortable" data-sort={sortConfig.key === 'year' ? sortConfig.direction : null}>
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
                                onDelete={() => this.deleteUserCourse(course.id)}
                            />
                        )}
                    </tbody>
                </table>
            </div>
        )
    }
}