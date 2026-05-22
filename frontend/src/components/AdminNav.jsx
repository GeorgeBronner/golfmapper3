import React from 'react';
import { NavLink } from 'react-router-dom';

const adminNavLinkClass = ({ isActive }) =>
    `admin-nav-link${isActive ? ' active' : ''}`;

const AdminNav = () => (
    <nav className="admin-topnav">
        <NavLink to="/admin/users" className={adminNavLinkClass}>
            User Management
        </NavLink>
    </nav>
);

export default AdminNav;
