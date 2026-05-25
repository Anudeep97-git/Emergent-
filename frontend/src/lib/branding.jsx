import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const DEFAULTS = {
    app_name: "Prima Nova",
    app_tagline: "Credit Risk Console",
    logo_initials: "PN",
    primary_color: "#0F172A",
    accent_color: "#6366F1",
    success_color: "#10B981",
    warning_color: "#F59E0B",
    danger_color: "#F43F5E",
    support_email: "support@primanova.com",
};

const BrandingCtx = createContext({ branding: DEFAULTS, refresh: () => {}, update: () => {}, reset: () => {} });

const _applyCSSVars = (b) => {
    const root = document.documentElement;
    root.style.setProperty("--pn-color-primary", b.primary_color);
    root.style.setProperty("--pn-color-accent", b.accent_color);
    root.style.setProperty("--pn-color-success", b.success_color);
    root.style.setProperty("--pn-color-warning", b.warning_color);
    root.style.setProperty("--pn-color-danger", b.danger_color);
    if (b.app_name) document.title = `${b.app_name} · Credit Risk`;
};

export const BrandingProvider = ({ children }) => {
    const [branding, setBranding] = useState(DEFAULTS);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const { data } = await api.get("/platform/branding");
            const merged = { ...DEFAULTS, ...data };
            setBranding(merged);
            _applyCSSVars(merged);
        } catch (_) {
            _applyCSSVars(DEFAULTS);
        } finally {
            setLoading(false);
        }
    }, []);

    const update = useCallback(async (patch) => {
        const { data } = await api.put("/platform/branding", patch);
        const merged = { ...DEFAULTS, ...data };
        setBranding(merged);
        _applyCSSVars(merged);
        return merged;
    }, []);

    const reset = useCallback(async () => {
        const { data } = await api.post("/platform/branding/reset");
        const merged = { ...DEFAULTS, ...data };
        setBranding(merged);
        _applyCSSVars(merged);
        return merged;
    }, []);

    useEffect(() => { refresh(); }, [refresh]);

    return (
        <BrandingCtx.Provider value={{ branding, loading, refresh, update, reset }}>
            {children}
        </BrandingCtx.Provider>
    );
};

export const useBranding = () => useContext(BrandingCtx);
