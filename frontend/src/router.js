import React from 'react';
import { createBrowserRouter, Outlet, Link } from 'react-router-dom';
import CourseList from './components/CourseList';
import CourseForm from './components/CourseForm';
import Map from './components/Map';
import LoginPage from './components/LoginPage';
import ProtectedRoute from './routes/ProtectedRoute';
import NewUser from './components/NewUser';
import GarminCourses from './components/GarminCourses';
import CourseSearch from './components/CourseSearch';

const router = createBrowserRouter([
    {
        element: <Outlet />,
        children: [
            { path: '/', element: <LoginPage /> },
            { path: '/register', element: <NewUser /> },
        ],
    },
    {
        element: <ProtectedRoute />,
        children: [
            { path: '/course_list', element: <CourseList /> },
            { path: '/add_course_by_id/:courseIdParam?', element: <CourseForm /> },
            { path: '/garmin_course_list', element: <GarminCourses /> },
            { path: '/map', element: <Map /> },
            { path: '/course_search', element: <CourseSearch /> },
        ],
    },
    {
        path: '*',
        element: (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <p>404 — Page not found.</p>
                <Link to="/">Back to login</Link>
            </div>
        ),
    },
]);

export default router;
