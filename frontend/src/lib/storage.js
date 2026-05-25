/**
 * Token storage abstraction — uses the new `prima_*` keys but transparently
 * migrates anything found under the legacy `c1b_*` keys on first read.
 */
const KEY_MAP = {
    token: { new: "prima_token", legacy: "c1b_token" },
    refresh: { new: "prima_refresh", legacy: "c1b_refresh" },
    user: { new: "prima_user", legacy: "c1b_user" },
};

const _migrate = (k) => {
    const m = KEY_MAP[k];
    if (!m) return null;
    const v = localStorage.getItem(m.new);
    if (v != null) return v;
    const legacy = localStorage.getItem(m.legacy);
    if (legacy != null) {
        localStorage.setItem(m.new, legacy);
        localStorage.removeItem(m.legacy);
        return legacy;
    }
    return null;
};

export const storage = {
    getToken: () => _migrate("token"),
    getRefresh: () => _migrate("refresh"),
    getUser: () => {
        const raw = _migrate("user");
        try { return raw ? JSON.parse(raw) : null; } catch { return null; }
    },
    setSession: ({ token, refresh_token, ...userPayload }) => {
        localStorage.setItem(KEY_MAP.token.new, token);
        if (refresh_token) localStorage.setItem(KEY_MAP.refresh.new, refresh_token);
        localStorage.setItem(KEY_MAP.user.new, JSON.stringify({ token, refresh_token, ...userPayload }));
        // best-effort cleanup of any legacy keys
        Object.values(KEY_MAP).forEach((m) => localStorage.removeItem(m.legacy));
    },
    clear: () => {
        Object.values(KEY_MAP).forEach((m) => {
            localStorage.removeItem(m.new);
            localStorage.removeItem(m.legacy);
        });
    },
};
