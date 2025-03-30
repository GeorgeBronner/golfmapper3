import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../config';

function CourseForm() {
    const { courseIdParam } = useParams();
    const [courseId, setCourse] = useState('');
    const [year, setYear] = useState('');

    useEffect(() => {
        if (courseIdParam && !isNaN(courseIdParam)) {
            setCourse(courseIdParam);
        }
    }, [courseIdParam]);

    const handleSubmit = (event) => {
        event.preventDefault();
        axios.post(`${API_BASE_URL}/user_courses/add_course`, {
            garmin_id: courseId,
            year: year,
        }, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
            .then(response => {
                console.log(response);
            })
            .catch(error => {
                console.error(error);
            });
        setCourse('');
        setYear('');
    };

    const generateUserMap = () => {
        axios.get(`${API_BASE_URL}/map/user_map_generate`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        })
            .then(response => {
                console.log(response);
            })
            .catch(error => {
                console.error(error);
            });
    };

    return (
        <div>
            <form onSubmit={handleSubmit}>
                <label>
                    CourseId:
                    <input type="text" value={courseId} onChange={e => setCourse(e.target.value)} />
                </label>
                <label>
                    Year:
                    <input type="text" value={year} onChange={e => setYear(e.target.value)} />
                </label>
                <input type="submit" value="Submit" />
            </form>
            <button onClick={generateUserMap}>Generate User Map</button>
        </div>
    );
}

export default CourseForm;