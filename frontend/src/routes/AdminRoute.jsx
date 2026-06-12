import React, { useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import Header from '../components/Header';
import AdminNav from '../components/AdminNav';
import { useAuth } from '../components/AuthProvider';

function getTokenPayload(token) {
    try {
        return JSON.parse(atob(token.split('.')[1]));
    } catch {
        return null;
    }
}

const AdminRoute = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const { token } = useAuth();

    if (!token) return <Navigate to="/" />;

    const payload = getTokenPayload(token);
    if (!payload || payload.exp * 1000 <= Date.now()) {
        return <Navigate to="/" />;
    }
    if (payload.role !== 'admin') return <Navigate to="/course_list" />;

    return (
        <div className="app-shell">
            <Header isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            {sidebarOpen && (
                <div
                    className="sidebar-overlay"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

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
                <AdminNav />
                <main className="main-content">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default AdminRoute;
