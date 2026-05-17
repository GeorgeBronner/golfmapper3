// src/ProtectedRoute.js
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Header from "../components/Header";
import Footer from "../components/Footer";

function isTokenValid(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp * 1000 > Date.now();
    } catch {
        return false;
    }
}

const ProtectedRoute = () => {
    const token = localStorage.getItem('token');
    if (!token || !isTokenValid(token)) {
        localStorage.removeItem('token');
        return <Navigate to="/" />;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <Header />
            <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <Outlet />
            </main>
            <Footer />
        </div>
    );
};

export default ProtectedRoute;