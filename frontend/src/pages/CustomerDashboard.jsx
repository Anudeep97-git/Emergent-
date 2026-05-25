import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useParams, Link } from "react-router-dom";
import { ChevronLeft, CreditCard, Wallet, Activity, IndianRupee } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "@/lib/api";
import RadialGauge from "@/components/RadialGauge";
import RiskBadge from "@/components/RiskBadge";
import SHAPTable from "@/components/SHAPTable";
import CreditDecisionCard from "@/components/CreditDecisionCard";
import ExportButton from "@/components/ExportButton";

const KPI = ({ icon: Icon, label, value, tint = "#6366F1", idx = 0 }) => (
    <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: idx * 0.08, duration: 0.4 }}
        className="bg-pn-card border border-pn-border rounded-2xl p-5"
        data-testid={`kpi-${label.toLowerCase().replace(/\s/g, "-")}`}
    >
        <div className="flex items-center justify-between mb-3">
            <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted">{label}</div>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${tint}1a` }}>
                <Icon className="w-4 h-4" style={{ color: tint }} />
            </div>
        </div>
        <div className="font-display text-2xl font-bold text-pn-primary tabular-nums">{value}</div>
    </motion.div>
);

export default function CustomerDashboardPage() {
    const { customerId } = useParams();
    const [profile, setProfile] = useState(null);
    const [decision, setDecision] = useState(null);
    const [spend, setSpend] = useState([]);
    const [batch, setBatch] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            setLoading(true);
            try {
                const [p, d, s, fr] = await Promise.all([
                    api.get(`/customer/profile/${customerId}`),
                    api.get(`/customer/decision/${customerId}`),
                    api.get(`/customer/spend-chart/${customerId}`),
                    api.get(`/customer/full-report/${customerId}`),
                ]);
                setProfile(p.data);
                setDecision(d.data);
                setSpend(s.data);
                setBatch(fr.data.phase4_batch_status);
            } finally {
                setLoading(false);
            }
        })();
    }, [customerId]);

    if (loading || !profile || !decision) {
        return (
            <div className="space-y-6">
                <div className="h-12 w-64 shimmer-bg rounded-xl" />
                <div className="grid grid-cols-4 gap-4">
                    {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 rounded-2xl shimmer-bg" />)}
                </div>
                <div className="h-72 rounded-2xl shimmer-bg" />
            </div>
        );
    }

    return (
        <div className="space-y-7">
            {/* Top bar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link
                        to="/portal"
                        data-testid="back-to-portal"
                        className="w-10 h-10 rounded-xl border border-pn-border bg-white flex items-center justify-center hover:bg-pn-surface transition"
                    >
                        <ChevronLeft className="w-5 h-5 text-pn-muted" />
                    </Link>
                    <div>
                        <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-1">
                            Customer Dashboard
                        </div>
                        <h1 className="font-display text-3xl sm:text-4xl font-bold text-pn-primary tracking-tight">
                            {customerId}
                        </h1>
                        <div className="text-sm text-pn-muted mt-1">
                            {profile.geography_region} · {profile.employment_status} · age {profile.age}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <RiskBadge label={decision.risk_label} size="lg" />
                    <ExportButton customerId={customerId} />
                </div>
            </div>

            {/* KPI row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPI idx={0} icon={CreditCard} label="Credit Limit" value={`₹${Math.round(profile.credit_limit / 1000)}k`} tint="#6366F1" />
                <KPI idx={1} icon={Wallet}      label="Balance"      value={`₹${Math.round(profile.current_balance / 1000)}k`} tint="#0F172A" />
                <KPI idx={2} icon={Activity}    label="Utilization"  value={`${(profile.utilization_rate * 100).toFixed(0)}%`}  tint="#F59E0B" />
                <KPI idx={3} icon={IndianRupee} label="Income"       value={`₹${Math.round(profile.income / 1000)}k`}           tint="#10B981" />
            </div>

            {/* Risk + SHAP + Decision */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="bg-pn-card border border-pn-border rounded-2xl p-6 flex flex-col items-center justify-center"
                >
                    <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-4">Risk Score</div>
                    <RadialGauge score={decision.risk_score} />
                    <div className="text-xs text-pn-muted mt-3 font-mono">{decision.risk_label} · {decision.action}</div>
                </motion.div>
                <div className="lg:col-span-2">
                    <SHAPTable factors={decision.contributing_factors} />
                </div>
            </div>

            <CreditDecisionCard decision={decision} />

            {/* Spend chart */}
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.2 }}
                className="bg-pn-card border border-pn-border rounded-2xl p-6"
                data-testid="spend-chart"
            >
                <div className="flex items-end justify-between mb-4">
                    <div>
                        <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted">Spend Trajectory</div>
                        <div className="font-display text-xl font-bold text-pn-primary tracking-tight">
                            12-Month Purchases & Cash Advances
                        </div>
                    </div>
                </div>
                <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={spend} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
                            <CartesianGrid stroke="#E2E8F0" strokeDasharray="2 4" />
                            <XAxis
                                dataKey="month"
                                tick={{ fontSize: 11, fill: "#94A3B8" }}
                                tickFormatter={(v) => v?.slice(0, 7)}
                            />
                            <YAxis tick={{ fontSize: 11, fill: "#94A3B8" }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
                            <Tooltip
                                contentStyle={{
                                    background: "white",
                                    border: "1px solid #E2E8F0",
                                    borderRadius: 12,
                                    fontSize: 12,
                                }}
                                formatter={(v) => `₹${Number(v).toLocaleString()}`}
                            />
                            <Line type="monotone" dataKey="purchases"     stroke="#6366F1" strokeWidth={2.5} dot={{ r: 3 }} />
                            <Line type="monotone" dataKey="cash_advances" stroke="#F43F5E" strokeWidth={2}   dot={{ r: 3 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </motion.div>

            {/* Pipeline status */}
            {batch && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.3 }}
                    className="bg-pn-card border border-pn-border rounded-2xl p-6"
                    data-testid="pipeline-status-card"
                >
                    <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-2">Pipeline Status</div>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                        <div className="font-display text-xl font-bold text-pn-primary tracking-tight">
                            Decision Pipeline
                        </div>
                        <div className="text-xs text-pn-muted">
                            Last run: <span className="font-mono text-pn-primary">{batch.batch_run_at}</span>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                        <div className="px-3 py-2.5 rounded-xl bg-pn-surface">
                            <div className="text-[10px] uppercase tracking-wider text-pn-muted">Batch Bucket</div>
                            <div className="text-sm font-semibold text-pn-primary">{decision.risk_label}</div>
                        </div>
                        <div className="px-3 py-2.5 rounded-xl bg-pn-surface">
                            <div className="text-[10px] uppercase tracking-wider text-pn-muted">Expand Eligible</div>
                            <div className="text-sm font-semibold" style={{ color: batch.eligible_expand ? "#10B981" : "#94A3B8" }}>
                                {batch.eligible_expand ? "Yes" : "No"}
                            </div>
                        </div>
                        <div className="px-3 py-2.5 rounded-xl bg-pn-surface">
                            <div className="text-[10px] uppercase tracking-wider text-pn-muted">Notification</div>
                            <div className="text-sm font-semibold" style={{ color: batch.notification_eligible ? "#6366F1" : "#94A3B8" }}>
                                {batch.notification_eligible ? "Scheduled" : "Suppressed"}
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
