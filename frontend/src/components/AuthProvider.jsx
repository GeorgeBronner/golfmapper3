import axios from "axios";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

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

    useEffect(() => {
        if (token) {
            axios.defaults.headers.common["Authorization"] = "Bearer " + token;
            localStorage.setItem('token',token);
        } else {
            delete axios.defaults.headers.common["Authorization"];
            localStorage.removeItem('token')
        }
    }, [token]);

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