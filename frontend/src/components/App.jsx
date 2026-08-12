import React, { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
// Use a relative path instead of the alias
import router from '../router';
import { SESSION_EXPIRED_EVENT } from '../constants/authEvents';
import './App.css';

function App() {
    // AuthProvider clears the token on SESSION_EXPIRED_EVENT; this navigates
    // away in-app (no hard reload) and leaves a message for the login page,
    // since a silent redirect gives the user no indication why they landed there.
    // replace: true so the now-invalid protected page isn't left one "back" away.
    useEffect(() => {
        const onSessionExpired = () => {
            sessionStorage.setItem('flashMessage', 'Your session has expired. Please log in again.');
            router.navigate('/', { replace: true });
        };
        window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
        return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    }, []);

    return (
        <div className="App">
            <RouterProvider router={router} />
        </div>
    );
}

export default App;