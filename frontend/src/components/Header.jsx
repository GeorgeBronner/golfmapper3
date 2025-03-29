import React from 'react';
import { Link, useNavigate} from 'react-router-dom';
import Navbar from "react-bootstrap/Navbar";
import Container from "react-bootstrap/Container";
import Nav from "react-bootstrap/Nav";
import Button from "react-bootstrap/Button";

function Header() {
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

    return (
        <div>

        <Navbar bg="light" data-bs-theme="light">
            <Container>
                <Navbar.Brand href="#home">Golf Mapper 2</Navbar.Brand>
                <Nav className="me-auto">
                    <Nav.Link href="/course_list">Home</Nav.Link>
                    <Nav.Link href="/add_course_by_id">Add Course</Nav.Link>
                    <Nav.Link href="/garmin_course_list">Course List</Nav.Link>
                    <Nav.Link href="/course_search">Course Search</Nav.Link>
                    <Nav.Link href="/map">Map</Nav.Link>
                    <Button onClick={handleLogout}>Logout</Button>
                </Nav>
            </Container>
        </Navbar>
        </div>
    );
}

export default Header;