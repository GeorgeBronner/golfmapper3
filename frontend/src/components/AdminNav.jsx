import React from 'react';
import { NavLink } from 'react-router-dom';

const adminNavLinkClass = ({ isActive }) =>
    `admin-nav-link${isActive ? ' active' : ''}`;

const AdminNav = () => (
    <nav className="admin-topnav">
        <NavLink to="/admin/users" className={adminNavLinkClass}>
            User Management
        </NavLink>
        <NavLink to="/admin/add-course" className={adminNavLinkClass}>
            Add Course
        </NavLink>
        <NavLink to="/admin/edit-course" className={adminNavLinkClass}>
            Edit Course Location
        </NavLink>
        <NavLink to="/admin/edit-course-info" className={adminNavLinkClass}>
            Edit Course Info
        </NavLink>
        <NavLink to="/admin/review-requests" className={adminNavLinkClass}>
            Review Requests
        </NavLink>
    </nav>
);

export default AdminNav;
