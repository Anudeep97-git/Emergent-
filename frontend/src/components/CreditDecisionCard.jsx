import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

const ACTION_MAP = {
    EXPAND:   { tint: "#10B981", verb: "Expand", desc: "Customer is eligible for limit expansion and APR reduction." },
    MONITOR:  { tint: "#F59E0B", verb: "Monitor", desc: "Hold current terms; reassess at next batch." },
    RESTRICT: { tint: "#F43F5E", verb: "Restrict", desc: "Reduce exposure: lower limit, raise APR." },
};

const Delta = ({ from, to, suffix = "", money = false }) => {
    const up = to > from;
    const same = Math.abs(to - from) < 1e-9;
    const Icon = same ? Minus : up ? ArrowUp : ArrowDown;
    const color = same ? "#94A3B8" : up ? "#10B981" : "#F43F5E";
    const fmt = (v) =>
        money
            ? "₹" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })
            : (Number(v) * 100).toFixed(2) + "%";
    return (
        <div className="flex items-center gap-2">
            <span className="text-c1b-muted text-sm">{fmt(from)}</span>
            <Icon className="w-4 h-4" style={{ color }} />
            <span className="font-bold text-c1b-primary" style={{ color }}>{fmt(to)}</span>
            {suffix && <span className="text-xs text-c1b-muted">{suffix}</span>}
        </div>
    );
};

export default function CreditDecisionCard({ decision }) {
    if (!decision) return null;
    const a = ACTION_MAP[decision.action] || ACTION_MAP.MONITOR;

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="bg-c1b-card border border-c1b-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
            data-testid="credit-decision-card"
        >
            <div className="flex items-start justify-between mb-5">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-c1b-muted mb-1">
                        Credit Decision
                    </div>
                    <div className="font-display text-2xl font-bold text-c1b-primary">
                        {a.verb} Credit
                    </div>
                </div>
                <div
                    className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider"
                    style={{ backgroundColor: `${a.tint}1a`, color: a.tint, border: `1px solid ${a.tint}55` }}
                >
                    {decision.action}
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-xl bg-c1b-surface">
                    <div className="text-xs uppercase tracking-wider text-c1b-muted">Credit Limit</div>
                    <Delta from={decision.current_limit} to={decision.recommended_limit} money />
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-c1b-surface">
                    <div className="text-xs uppercase tracking-wider text-c1b-muted">APR</div>
                    <Delta from={decision.current_apr} to={decision.recommended_apr} />
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-c1b-surface">
                    <div className="text-xs uppercase tracking-wider text-c1b-muted">Opportunity Rank</div>
                    <div className="text-sm font-semibold text-c1b-primary">
                        #{decision.opportunity_rank} / 100 ·{" "}
                        <span className="text-c1b-muted font-mono">
                            score {decision.opportunity_score?.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            <p className="mt-4 text-xs text-c1b-muted leading-relaxed">{a.desc}</p>
        </motion.div>
    );
}
