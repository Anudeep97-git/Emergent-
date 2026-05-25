import axios from "axios";
import { storage } from "@/lib/storage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({
    baseURL: API_BASE,
    headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((cfg) => {
    const tok = storage.getToken();
    if (tok) cfg.headers.Authorization = `Bearer ${tok}`;
    return cfg;
});

api.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err?.response?.status === 401) {
            storage.clear();
            if (!window.location.pathname.startsWith("/login")) {
                window.location.href = "/login";
            }
        }
        return Promise.reject(err);
    }
);
