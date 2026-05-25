import React from 'react';
import { NavLink } from 'react-router-dom';

const navLinkClass = ({ isActive }) =>
    `admin-nav-link${isActive ? ' active' : ''}`;

const CourseEditsNav = () => (
    <nav className="admin-topnav" style={{ display: 'flex', alignItems: 'center' }}>
        <NavLink to="/course_edits/new-course" className={navLinkClass}>
            Request New Course
        </NavLink>
        <NavLink to="/course_edits/location-change" className={navLinkClass}>
            Request Location Change
        </NavLink>
        <span className="ms-auto me-3 text-muted" style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
            Requests are reviewed by an admin before taking effect
        </span>
    </nav>
);

export default CourseEditsNav;
