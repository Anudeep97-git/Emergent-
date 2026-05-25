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

const BrandingCtx = createContext({
    branding: DEFAULTS,
    loading: true,
    refresh: () => {},
    update: () => {},
    reset: () => {},
});

// "#0F172A" -> "15 23 42"  (Tailwind alpha-channel friendly)
const hexToRgbTriplet = (hex) => {
    if (!hex || typeof hex !== "string") return null;
    const h = hex.replace("#", "").trim();
    const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
    if (full.length !== 6) return null;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    if ([r, g, b].some((n) => Number.isNaN(n))) return null;
    return `${r} ${g} ${b}`;
};

const _applyCSSVars = (b) => {
    const root = document.documentElement;
    const map = {
        "--pn-primary": b.primary_color,
        "--pn-accent": b.accent_color,
        "--pn-success": b.success_color,
        "--pn-warning": b.warning_color,
        "--pn-danger": b.danger_color,
    };
    Object.entries(map).forEach(([cssVar, hex]) => {
        const triplet = hexToRgbTriplet(hex);
        if (triplet) root.style.setProperty(cssVar, triplet);
    });
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
