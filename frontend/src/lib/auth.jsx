import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { storage } from "@/lib/storage";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(() => storage.getUser());
    const [loading, setLoading] = useState(false);

    const login = async (email, password) => {
        setLoading(true);
        try {
            const { data } = await api.post("/auth/login", { email, password });
            storage.setSession(data);
            setUser(data);
            return data;
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        try { await api.post("/auth/logout"); } catch (_) {}
        storage.clear();
        setUser(null);
    };

    useEffect(() => {
        const onStorage = () => setUser(storage.getUser());
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
