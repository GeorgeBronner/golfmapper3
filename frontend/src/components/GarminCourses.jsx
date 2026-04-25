import React from 'react';
import api from '../services/api';
import GarminCourseRow from "./GarminCourseRow";

export default class GarminCourses extends React.Component {
    state = {
        courses: []
    }

    componentDidMount() {
        this.fetchCourses();
    }

    fetchCourses = () => {
        api.get('/readall')
            .then(res => {
                const courses = res.data;
                this.setState({ courses });
            })
    }

    deleteUserCourse = (id) => {
        api.delete(`/user_courses/delete/${id}`)
            .then(() => {
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
                        {this.state.courses.map(course =>
                            <GarminCourseRow
                                key={course.id}
                                id={course.id}
                                display_name={course.display_name}
                                city={course.city}
                                state={course.state}
                                country={course.country}
                                onDelete={() => this.deleteUserCourse(course.id)}
                            />
                        )}
                    </tbody>
                </table>
            </div>
        )
    }
}
