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
    </nav>
);

export default AdminNav;
