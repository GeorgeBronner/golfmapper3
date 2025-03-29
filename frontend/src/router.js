import React from 'react';
import {createBrowserRouter, Outlet} from 'react-router-dom';
import CourseList from "./components/CourseList";
import CourseForm from "./components/CourseForm";
import Map from "./components/Map";
import LoginPage from "./components/LoginPage";
import ProtectedRoute from "./routes/ProtectedRoute";
import PageAfterAuth from "./components/PageAfterAuth";
import Footer from "./components/Footer";
import NewUser from "./components/NewUser";
import LoginHeader from "./components/LoginHeader";
import GarminCourses from "./components/GarminCourses";
import CourseSearch from "./components/CourseSearch";

// Function to get the access token from cookies
const getAccessToken = () => {
    return localStorage.getItem('token');
}

// Function to check if the user is authenticated
const isAuthenticated = () => {
    return !!getAccessToken();
}

const Layout = () => (
    <>
        <LoginHeader />
        <Outlet />
        <Footer/>
    </>
);

// Create the router configuration
const router = createBrowserRouter(
    [
        {
            element: <Layout />,
            children: [
                {
                    path: '/',
                    element: <LoginPage />,
                    index: true
                },
                {
                    path: '/register',
                    element: <NewUser />,
                    index: true
                },
            ]
        },
        {
            element: <ProtectedRoute isAuthenticated={isAuthenticated()} />,
            children: [
                {
                    path: '/course_list',
                    element: <CourseList />
                },
                {
                    path: '/add_course_by_id/:courseIdParam?',
                    element: <CourseForm />
                },
                {
                    path: '/garmin_course_list',
                    element: <GarminCourses />
                },
                {
                    path: '/PageAfterAuth',
                    element: <PageAfterAuth />
                },
                {
                    path: '/map',
                    element: <Map />
                },
                {
                    path: '/course_search',
                    element: <CourseSearch />
                },
            ]
        },
        {
            path: '*',
            element: <div><p>404 Error - Are you logged in?</p><a href='/'> Click here to login</a> </div>
        }
    ]
);

export default router;