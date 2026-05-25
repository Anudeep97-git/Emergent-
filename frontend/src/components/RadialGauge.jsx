import { motion } from "framer-motion";

/**
 * Animated SVG radial gauge — arc draw 0 → score, 600ms ease-in-out per PRD §7.7.
 * size = diameter in px, score in [0, 1].
 */
export default function RadialGauge({ score = 0, label = "Risk", size = 200 }) {
    const radius = size / 2 - 14;
    const circ = 2 * Math.PI * radius;
    const dash = circ * (1 - Math.min(Math.max(score, 0), 1));

    let stroke = "#10B981"; // success
    if (score >= 0.66) stroke = "#F43F5E";       // danger
    else if (score >= 0.33) stroke = "#F59E0B"; // warning

    return (
        <div className="relative inline-flex items-center justify-center" data-testid="radial-gauge">
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="#E2E8F0"
                    strokeWidth="10"
                />
                <motion.circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={stroke}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    animate={{ strokeDashoffset: dash }}
                    transition={{ duration: 0.6, ease: "easeInOut" }}
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.4 }}
                    className="font-display text-3xl font-bold tracking-tight text-pn-primary"
                    data-testid="radial-gauge-value"
                >
                    {(score * 100).toFixed(1)}%
                </motion.div>
                <div className="text-[10px] uppercase tracking-[0.22em] text-pn-muted mt-0.5">{label}</div>
            </div>
        </div>
    );
}
