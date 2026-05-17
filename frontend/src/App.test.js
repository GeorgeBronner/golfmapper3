import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import LoginPage from './components/LoginPage';
import AuthProvider from './components/AuthProvider';
import ProtectedRoute from './routes/ProtectedRoute';

function renderWithProviders(ui, { initialEntries = ['/'] } = {}) {
    return render(
        <AuthProvider>
            <MemoryRouter initialEntries={initialEntries}>
                {ui}
            </MemoryRouter>
        </AuthProvider>
    );
}

describe('LoginPage', () => {
    it('renders username and password fields', () => {
        renderWithProviders(<LoginPage />);
        expect(screen.getByText(/username/i)).toBeInTheDocument();
        expect(screen.getByText(/password/i)).toBeInTheDocument();
    });

    it('renders a login submit button', () => {
        renderWithProviders(<LoginPage />);
        expect(screen.getByDisplayValue(/login/i)).toBeInTheDocument();
    });

    it('does not show an error message on initial render', () => {
        renderWithProviders(<LoginPage />);
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
});

describe('ProtectedRoute', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it('redirects to login when no token is present', () => {
        renderWithProviders(
            <Routes>
                <Route path="/" element={<LoginPage />} />
                <Route element={<ProtectedRoute />}>
                    <Route path="/course_list" element={<div>Protected Content</div>} />
                </Route>
            </Routes>,
            { initialEntries: ['/course_list'] }
        );

        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
        expect(screen.getByText(/username/i)).toBeInTheDocument();
    });
});
