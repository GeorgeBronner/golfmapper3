import React from 'react';
import axios from 'axios';
import CourseCard from "./CourseCard";

export default class GarminCourses extends React.Component {


    state = {
        courses: []
    }

    componentDidMount() {

        axios.get(`http://127.0.0.1:8000/readall`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }})
            .then(res => {
                const courses = res.data;
                this.setState({ courses });
            })
    }

    deleteUserCourse = (id) => {
        axios.delete(`http://127.0.0.1:8000/user_courses/delete/${id}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }})
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
            <div className="course-list-container">
                {
                    this.state.courses.map(course =>
                        <div key={course.id} className="courseCard">
                            <CourseCard g_course={course.g_course} g_city={course.g_city} year={course.year} onDelete={() => this.deleteUserCourse(course.id)}/>
                        </div>
                    )
                }
            </div>
        )
    }
}