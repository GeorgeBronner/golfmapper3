// src/ProtectedRoute.js
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Header from "../components/Header";
import Footer from "../components/Footer";

const ProtectedRoute = ({ isAuthenticated }) => {
    if (!isAuthenticated) {
        return <Navigate to="/course_list" />;
    }

    return <div>
    <Header />
    <Outlet />
    <Footer />
    </div>;
};

export default ProtectedRoute;