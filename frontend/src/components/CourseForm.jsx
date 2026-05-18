import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';
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
        api.post('/user_courses/add_course', { garmin_id: courseId, year })
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
            <div className="page-header">
                <div>
                    <div className="page-title">Add Course</div>
                    <div className="page-subtitle">Enter a Garmin course ID and the year you played it</div>
                </div>
            </div>

            <div className="form-card">
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="course-id">Course ID</label>
                        <input
                            id="course-id"
                            className="form-input"
                            type="text"
                            value={courseId}
                            onChange={e => setCourse(e.target.value)}
                            placeholder="e.g. 12345"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="course-year">Year Played</label>
                        <input
                            id="course-year"
                            className="form-input"
                            type="number"
                            value={year}
                            onChange={e => setYear(e.target.value)}
                            placeholder={new Date().getFullYear()}
                            min="1900"
                            max={new Date().getFullYear()}
                        />
                    </div>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <button type="submit" className="btn-primary">Add Course</button>
                        <button type="button" className="btn-ghost" onClick={generateUserMap}>
                            🗺 Regenerate Map
                        </button>
                    </div>
                </form>

                {success && <div className="alert-success">{success}</div>}
                {error && <div className="alert-danger">{error}</div>}
            </div>
        </div>
    );
}

export default CourseForm;
