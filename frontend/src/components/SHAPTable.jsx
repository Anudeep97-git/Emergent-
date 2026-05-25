import { motion } from "framer-motion";
import { featureLabel } from "@/lib/labels";

/** Top-5 contributing factors with staggered reveal (0.1s/row). */
export default function SHAPTable({ factors = {} }) {
    const rows = Object.entries(factors).slice(0, 5);
    const max = Math.max(...rows.map(([, v]) => v), 0.0001);

    return (
        <div className="space-y-2" data-testid="shap-table">
            <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-pn-muted">
                <span>Top Risk Drivers</span>
                <span>Impact</span>
            </div>
            <div className="border border-pn-border rounded-2xl bg-white overflow-hidden">
                {rows.map(([feat, val], i) => (
                    <motion.div
                        key={feat}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1, duration: 0.4 }}
                        className="flex items-center gap-3 px-4 py-3 border-b border-pn-border last:border-b-0"
                        data-testid={`shap-row-${i}`}
                    >
                        <div className="w-5 h-5 rounded-md bg-pn-primary text-white text-[10px] font-bold flex items-center justify-center">
                            {i + 1}
                        </div>
                        <div className="text-sm text-pn-ink flex-1 truncate">{featureLabel(feat)}</div>
                        <div className="w-32 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${(val / max) * 100}%` }}
                                transition={{ delay: i * 0.1 + 0.2, duration: 0.5 }}
                                className="h-full bg-pn-accent rounded-full"
                            />
                        </div>
                        <div className="text-xs font-semibold text-pn-primary w-16 text-right tabular-nums">
                            {val.toFixed(3)}
                        </div>
                    </motion.div>
                ))}
                {rows.length === 0 && (
                    <div className="p-6 text-center text-sm text-pn-muted">No key factors available.</div>
                )}
            </div>
        </div>
    );
}
