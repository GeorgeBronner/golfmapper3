import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const CourseSearch = () => {
    const [courses, setCourses] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const pageSize = 50; // Set pageSize as a constant

    const fetchCourses = useCallback(async () => {
        try {
            const response = await axios.get('http://127.0.0.1:8000/readall_page', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                params: {
                    search: searchTerm,
                    page: currentPage,
                    size: pageSize
                }
            });
            console.log('API Response:', response.data);
            setCourses(response.data.items || []);
            setTotalPages(response.data.pages || 1);
            console.log('Updated Courses State:', response.data.items || []);
        } catch (error) {
            console.error('Error fetching courses:', error);
        }
    }, [searchTerm, currentPage, pageSize]);

    useEffect(() => {
        fetchCourses();
    }, [fetchCourses]);

    const handleSearchChange = (event) => {
        setSearchTerm(event.target.value);
        setCurrentPage(1);
    };

    const handlePageChange = (newPage) => {
        setCurrentPage(newPage);
    };

    return (
        <div>
            <div>
                <label>
                    Course Name:
                    <input type="text" value={searchTerm} onChange={handleSearchChange} />
                </label>
            </div>
            <div>
                {Array.isArray(courses) && courses.map(course => (
                    <div key={course.id}>
                        <h3>{course.display_name}</h3>
                        <p>{course.city}</p>
                        <p>{course.id}</p>
                    </div>
                ))}
            </div>
            <div>
                {Array.from({ length: totalPages }, (_, index) => (
                    <button
                        key={index}
                        onClick={() => handlePageChange(index + 1)}
                        disabled={currentPage === index + 1}
                    >
                        {index + 1}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default CourseSearch;