import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import LoginPage from './components/LoginPage';

describe('LoginPage', () => {
    it('renders username and password fields', () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );
        expect(screen.getByText(/username/i)).toBeInTheDocument();
        expect(screen.getByText(/password/i)).toBeInTheDocument();
    });

    it('renders a login submit button', () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );
        expect(screen.getByDisplayValue(/login/i)).toBeInTheDocument();
    });

    it('does not show an error message on initial render', () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
});

describe('ProtectedRoute', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it('redirects to login when no token is present', async () => {
        const { default: ProtectedRoute } = await import('./routes/ProtectedRoute');
        const { default: LoginPage } = await import('./components/LoginPage');
        const { Routes, Route } = await import('react-router-dom');

        render(
            <MemoryRouter initialEntries={['/course_list']}>
                <Routes>
                    <Route path="/" element={<LoginPage />} />
                    <Route element={<ProtectedRoute />}>
                        <Route path="/course_list" element={<div>Protected Content</div>} />
                    </Route>
                </Routes>
            </MemoryRouter>
        );

        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
        expect(screen.getByText(/username/i)).toBeInTheDocument();
    });
});
