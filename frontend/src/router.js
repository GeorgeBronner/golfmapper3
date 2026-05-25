import React from 'react';
import { createBrowserRouter, Navigate, Outlet, Link } from 'react-router-dom';
import CourseList from './components/CourseList';
import CourseForm from './components/CourseForm';
import Map from './components/Map';
import AllUsersMap from './components/AllUsersMap';
import LoginPage from './components/LoginPage';
import ProtectedRoute from './routes/ProtectedRoute';
import AdminRoute from './routes/AdminRoute';
import NewUser from './components/NewUser';
import CourseSearch from './components/CourseSearch';
import UserProfile from './components/UserProfile';
import AdminUsers from './components/AdminUsers';
import AdminAddCourse from './components/AdminAddCourse';
import AdminEditCourse from './components/AdminEditCourse';
import AdminReviewRequests from './components/AdminReviewRequests';
import AdminEditCourseInfo from './components/AdminEditCourseInfo';
import CourseEdits from './components/CourseEdits';
import CourseEditsNewCourse from './components/CourseEditsNewCourse';
import CourseEditsLocationChange from './components/CourseEditsLocationChange';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';

const router = createBrowserRouter([
    {
        element: <Outlet />,
        children: [
            { path: '/', element: <LoginPage /> },
            { path: '/register', element: <NewUser /> },
            { path: '/forgot-password', element: <ForgotPassword /> },
            { path: '/reset-password', element: <ResetPassword /> },
        ],
    },
    {
        element: <ProtectedRoute />,
        children: [
            { path: '/course_list', element: <CourseList /> },
            { path: '/add_course_by_id/:courseIdParam?', element: <CourseForm /> },
            { path: '/map', element: <Map /> },
            { path: '/all_map', element: <AllUsersMap /> },
            { path: '/course_search', element: <CourseSearch /> },
            { path: '/profile', element: <UserProfile /> },
            {
                path: '/course_edits',
                element: <CourseEdits />,
                children: [
                    { index: true, element: <Navigate to="new-course" replace /> },
                    { path: 'new-course', element: <CourseEditsNewCourse /> },
                    { path: 'location-change', element: <CourseEditsLocationChange /> },
                ],
            },
        ],
    },
    {
        element: <AdminRoute />,
        children: [
            { path: '/admin/users', element: <AdminUsers /> },
            { path: '/admin/add-course', element: <AdminAddCourse /> },
            { path: '/admin/edit-course', element: <AdminEditCourse /> },
            { path: '/admin/edit-course-info', element: <AdminEditCourseInfo /> },
            { path: '/admin/review-requests', element: <AdminReviewRequests /> },
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
