import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import { API_BASE_URL } from '../config';
import { generateUserMap } from '../utils/mapUtils';

function CourseForm() {
    const { courseIdParam } = useParams();
    const [courseId, setCourse] = useState('');
    const [year, setYear] = useState('');
    const [success, setSuccess] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        if (courseIdParam && !isNaN(courseIdParam)) {
            setCourse(courseIdParam);
        }
    }, [courseIdParam]);

    const handleSubmit = (event) => {
        event.preventDefault();
        setSuccess('');
        setError('');
        axios.post(`${API_BASE_URL}/user_courses/add_course`, {
            garmin_id: courseId,
            year: year,
        }, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
            .then(() => {
                setSuccess('Course added successfully.');
                setCourse('');
                setYear('');
            })
            .catch(err => {
                const status = err.response?.status;
                if (status === 409) {
                    setError('You have already added this course for that year.');
                } else if (status === 422) {
                    setError('Invalid course ID or year.');
                } else {
                    setError('Failed to add course. Please try again.');
                }
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
                    <input type="number" value={year} onChange={e => setYear(e.target.value)} />
                </label>
                <input type="submit" value="Submit" />
            </form>
            {success && <div className="alert alert-success">{success}</div>}
            {error && <div className="alert alert-danger">{error}</div>}
            <button onClick={generateUserMap}>Generate User Map</button>
        </div>
    );
}

export default CourseForm;
