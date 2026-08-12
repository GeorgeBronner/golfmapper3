import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { SESSION_EXPIRED_EVENT } from '../constants/authEvents';

const AuthContext = createContext();

const getUserRole = (tkn) => {
    if (!tkn) return null;
    try {
        return JSON.parse(atob(tkn.split('.')[1])).role ?? null;
    } catch { return null; }
};

const getUsername = (tkn) => {
    if (!tkn) return null;
    try {
        return JSON.parse(atob(tkn.split('.')[1])).sub ?? null;
    } catch { return null; }
};

const AuthProvider = ({ children }) => {
    const [token, setToken_] = useState(localStorage.getItem("token"));

    const setToken = (newToken) => {
        setToken_(newToken);
    };

    // The api service (services/api.js) reads the token from localStorage on
    // every request, so keeping localStorage in sync is all that's needed here.
    useEffect(() => {
        if (token) {
            localStorage.setItem('token', token);
        } else {
            localStorage.removeItem('token');
        }
    }, [token]);

    // api.js clears localStorage directly on a 401 (it has no access to this
    // context) and dispatches this event so our own state stays in sync.
    useEffect(() => {
        const onSessionExpired = () => setToken_(null);
        window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
        return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    }, []);

    const contextValue = useMemo(
        () => ({
            token,
            setToken,
            userRole: getUserRole(token),
            username: getUsername(token),
        }),
        [token]
    );

    // Provide the authentication context to the children components
    return (
        <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
    );
};

export const useAuth = () => {
    return useContext(AuthContext);
};

export default AuthProvider;