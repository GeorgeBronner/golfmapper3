import React, { useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Header from '../components/Header';

function isTokenValid(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp * 1000 > Date.now();
    } catch {
        return false;
    }
}

const ProtectedRoute = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const token = localStorage.getItem('token');
    if (!token || !isTokenValid(token)) {
        localStorage.removeItem('token');
        return <Navigate to="/" />;
    }

    return (
        <div className="app-shell">
            {/* Sidebar — desktop: static column 1. Mobile: position:fixed when open. */}
            <Header isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            {/* Backdrop for mobile sidebar */}
            {sidebarOpen && (
                <div
                    className="sidebar-overlay"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Right-hand content column */}
            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
                <div className="mobile-topbar">
                    <span className="mobile-brand">⛳ GolfMapper</span>
                    <button
                        className="mobile-hamburger"
                        onClick={() => setSidebarOpen(true)}
                        aria-label="Open menu"
                    >
                        ☰
                    </button>
                </div>
                <main className="main-content">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default ProtectedRoute;
