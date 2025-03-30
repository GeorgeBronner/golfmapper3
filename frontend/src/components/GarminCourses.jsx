import React from 'react';
import axios from 'axios';
import GarminCourseRow from "./GarminCourseRow";
import { API_BASE_URL } from '../config';

export default class GarminCourses extends React.Component {
    state = {
        courses: []
    }

    componentDidMount() {
        this.fetchCourses();
    }

    fetchCourses = () => {
        axios.get(`${API_BASE_URL}/readall`, {
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

    render() {
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
                        {this.state.courses.slice(1).map(course =>
                            <GarminCourseRow 
                                key={course.id}
                                id={course.id}
                                g_course={course.g_course} 
                                g_city={course.g_city}
                                g_state={course.g_state}
                                g_country={course.g_country}
                                onDelete={() => this.deleteUserCourse(course.id)}
                            />
                        )}
                    </tbody>
                </table>
            </div>
        )
    }
}