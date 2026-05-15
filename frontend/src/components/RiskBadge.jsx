import { motion } from "framer-motion";

const MAP = {
    LOW:    { color: "#10B981", glow: "rgba(16,185,129,0.45)", emoji: "🟢", label: "Low Risk" },
    MEDIUM: { color: "#F59E0B", glow: "rgba(245,158,11,0.45)", emoji: "🟡", label: "Medium Risk" },
    HIGH:   { color: "#F43F5E", glow: "rgba(244,63,94,0.45)",  emoji: "🔴", label: "High Risk" },
};

export default function RiskBadge({ label = "LOW", size = "md" }) {
    const cfg = MAP[label] || MAP.LOW;
    const padding = size === "lg" ? "px-4 py-1.5 text-sm" : "px-3 py-1 text-xs";

    return (
        <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className={`inline-flex items-center gap-2 rounded-full font-semibold uppercase tracking-wider ${padding}`}
            style={{
                backgroundColor: `${cfg.color}1a`,
                color: cfg.color,
                border: `1px solid ${cfg.color}55`,
                "--pulse-color": cfg.glow,
            }}
            data-testid={`risk-badge-${label.toLowerCase()}`}
        >
            <span
                className="inline-block w-2 h-2 rounded-full animate-pulse-ring"
                style={{ backgroundColor: cfg.color, boxShadow: `0 0 0 0 ${cfg.glow}` }}
            />
            {cfg.label}
        </motion.div>
    );
}
