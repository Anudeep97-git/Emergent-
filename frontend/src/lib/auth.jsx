import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(() => {
        const raw = localStorage.getItem("c1b_user");
        return raw ? JSON.parse(raw) : null;
    });
    const [loading, setLoading] = useState(false);

    const login = async (email, password) => {
        setLoading(true);
        try {
            const { data } = await api.post("/auth/login", { email, password });
            localStorage.setItem("c1b_token", data.token);
            localStorage.setItem("c1b_refresh", data.refresh_token);
            localStorage.setItem("c1b_user", JSON.stringify(data));
            setUser(data);
            return data;
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try { await api.post("/auth/logout"); } catch (_) {}
        localStorage.removeItem("c1b_token");
        localStorage.removeItem("c1b_refresh");
        localStorage.removeItem("c1b_user");
        setUser(null);
    };

    useEffect(() => {
        // Keep state in sync if user logs out in another tab
        const onStorage = () => {
            const raw = localStorage.getItem("c1b_user");
            setUser(raw ? JSON.parse(raw) : null);
        };
        window.addEventListener("storage", onStorage);
        return () => window.removeEventListener("storage", onStorage);
    }, []);

    return (
        <AuthCtx.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthCtx.Provider>
    );
};

export const useAuth = () => useContext(AuthCtx);
