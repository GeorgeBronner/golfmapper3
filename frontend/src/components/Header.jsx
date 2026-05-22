import React from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

function Header({ isOpen, onClose }) {
    const navigate = useNavigate();
    const { setToken, userRole } = useAuth();

    const handleLogout = () => {
        setToken(null);
        navigate('/');
    };

    const navLinkClass = ({ isActive }) =>
        `nav-item${isActive ? ' active' : ''}`;

    return (
        <nav className={`sidebar${isOpen ? ' open' : ''}`} role="navigation">
            <Link to="/course_list" className="sidebar-brand" onClick={onClose}>
                ⛳ GolfMapper
            </Link>

            <div className="nav-section">
                <div className="nav-section-label">Navigation</div>
                <NavLink to="/course_list" className={navLinkClass} onClick={onClose}>
                    <span className="nav-icon">📋</span> My Courses
                </NavLink>
                <NavLink to="/map" className={navLinkClass} onClick={onClose}>
                    <span className="nav-icon">🗺</span> My Map
                </NavLink>
                <NavLink to="/course_search" className={navLinkClass} onClick={onClose}>
                    <span className="nav-icon">🔍</span> Course Search
                </NavLink>
                <NavLink to="/add_course_by_id" className={navLinkClass} onClick={onClose}>
                    <span className="nav-icon">➕</span> Add Course
                </NavLink>
                <NavLink to="/garmin_course_list" className={navLinkClass} onClick={onClose}>
                    <span className="nav-icon">📂</span> All Courses
                </NavLink>
                {userRole === 'admin' && (
                    <NavLink to="/admin/users" className={navLinkClass} onClick={onClose}>
                        <span className="nav-icon">⚙️</span> Admin
                    </NavLink>
                )}
            </div>

            <div className="sidebar-divider" />

            <div className="nav-section">
                <button className="btn-logout" onClick={handleLogout}>
                    <span className="nav-icon">🚪</span> Logout
                </button>
            </div>

            <div className="sidebar-footer">
                GolfMapper · v3
            </div>
        </nav>
    );
}

export default Header;
