import React from 'react';
import axios from 'axios';
import CourseCard from "./CourseCard";

export default class PageAfterAuth extends React.Component {
    state = {
        courses: []
    }

    componentDidMount() {
        axios.get(`http://127.0.0.1:8005/user_courses_no_auth/readall`)
            .then(res => {
                const courses = res.data;
                this.setState({ courses });
            })
    }

    deleteUserCourse = (id) => {
        axios.delete(`http://127.0.0.1:8005/user_courses_no_auth/delete/${id}`)
            .then(response => {
                console.log(response);
                // After deleting the course, fetch the updated list of courses
                this.componentDidMount();
            })
            .catch(error => {
                console.error(error);
            });
    }

    render() {
        return (
            <ul>
                {
                    this.state.courses
                        .map(course =>
                            <CourseCard g_course={course.g_course} g_city={course.g_city} onDelete={() => this.deleteUserCourse(course.id)}/>
                        )
                }
            </ul>
        )
    }
}