import React, { Suspense, lazy } from 'react';
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
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';

// Lazy-load the admin pages and the leaflet/bootstrap-heavy course-edit pages
// so they don't weigh down the initial bundle.
const AdminUsers = lazy(() => import('./components/AdminUsers'));
const AdminAddCourse = lazy(() => import('./components/AdminAddCourse'));
const AdminEditCourse = lazy(() => import('./components/AdminEditCourse'));
const AdminReviewRequests = lazy(() => import('./components/AdminReviewRequests'));
const AdminEditCourseInfo = lazy(() => import('./components/AdminEditCourseInfo'));
const CourseEdits = lazy(() => import('./components/CourseEdits'));
const CourseEditsNewCourse = lazy(() => import('./components/CourseEditsNewCourse'));
const CourseEditsLocationChange = lazy(() => import('./components/CourseEditsLocationChange'));

const withSuspense = (element) => (
    <Suspense fallback={<p className="loading-text">Loading…</p>}>
        {element}
    </Suspense>
);

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
                element: withSuspense(<CourseEdits />),
                children: [
                    { index: true, element: <Navigate to="new-course" replace /> },
                    { path: 'new-course', element: withSuspense(<CourseEditsNewCourse />) },
                    { path: 'location-change', element: withSuspense(<CourseEditsLocationChange />) },
                ],
            },
        ],
    },
    {
        element: <AdminRoute />,
        children: [
            { path: '/admin/users', element: withSuspense(<AdminUsers />) },
            { path: '/admin/add-course', element: withSuspense(<AdminAddCourse />) },
            { path: '/admin/edit-course', element: withSuspense(<AdminEditCourse />) },
            { path: '/admin/edit-course-info', element: withSuspense(<AdminEditCourseInfo />) },
            { path: '/admin/review-requests', element: withSuspense(<AdminReviewRequests />) },
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
