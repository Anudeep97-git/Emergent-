import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Search, Filter, ArrowUpRight, Users, AlertCircle, BadgeCheck, Activity } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import RiskBadge from "@/components/RiskBadge";
import SystemHealthPanel from "@/components/SystemHealthPanel";
import { useAuth } from "@/lib/auth";

const FILTERS = ["ALL", "HIGH", "MEDIUM", "LOW"];

const KPI = ({ icon: Icon, label, value, tint, idx }) => (
    <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: idx * 0.08 }}
        className="bg-c1b-card border border-c1b-border rounded-2xl p-5 hover:shadow-md hover:scale-[1.02] transition-all duration-200"
        data-testid={`kpi-${label.toLowerCase().replace(/\s/g, "-")}`}
    >
        <div className="flex items-center justify-between mb-3">
            <div className="text-[11px] uppercase tracking-[0.22em] text-c1b-muted">{label}</div>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${tint}1a` }}>
                <Icon className="w-4 h-4" style={{ color: tint }} />
            </div>
        </div>
        <div className="font-display text-3xl font-bold text-c1b-primary tracking-tight">{value}</div>
    </motion.div>
);

export default function CustomerPortalPage() {
    const { user } = useAuth();
    const [customers, setCustomers] = useState([]);
    const [summary, setSummary] = useState(null);
    const [filter, setFilter] = useState("ALL");
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const [c, s] = await Promise.all([api.get("/customer/all"), api.get("/dashboard/summary")]);
                setCustomers(c.data);
                setSummary(s.data);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const filtered = customers.filter((c) => {
        if (filter !== "ALL" && c.risk_label !== filter) return false;
        if (query && !c.customer_id.toLowerCase().includes(query.toLowerCase())) return false;
        return true;
    });

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-end justify-between flex-wrap gap-4">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-c1b-muted mb-2">
                        Prima Nova
                    </div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold text-c1b-primary tracking-tight">
                        Customer Risk Portal
                    </h1>
                    <p className="text-c1b-muted mt-2 text-sm max-w-xl">
                        Click any customer card to drill into the full risk profile, key factors, and credit decision.
                    </p>
                </div>
            </div>

            {/* KPIs */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <KPI idx={0} icon={Users}      label="Total Customers" value={summary.total_customers}                tint="#6366F1" />
                    <KPI idx={1} icon={AlertCircle} label="High Risk"       value={summary.high_risk}                       tint="#F43F5E" />
                    <KPI idx={2} icon={Activity}    label="Medium Risk"     value={summary.medium_risk}                     tint="#F59E0B" />
                    <KPI idx={3} icon={BadgeCheck}  label="Low Risk"        value={summary.low_risk}                        tint="#10B981" />
                    <KPI idx={4} icon={ArrowUpRight} label="Avg Risk Score" value={(summary.avg_risk_score * 100).toFixed(1) + "%"} tint="#0F172A" />
                </div>
            )}

            {/* Operations (admin-only, collapsed by default) */}
            <SystemHealthPanel user={user} />

            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap">
                <div className="relative flex-1 min-w-[240px] max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-c1b-muted" />
                    <Input
                        data-testid="portal-search-input"
                        placeholder="Search by customer_id (e.g. C001)"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="pl-10 h-11 bg-white border-c1b-border"
                    />
                </div>
                <div className="flex items-center gap-1 bg-white border border-c1b-border rounded-xl p-1">
                    <Filter className="w-4 h-4 text-c1b-muted mx-2" />
                    {FILTERS.map((f) => (
                        <Button
                            key={f}
                            data-testid={`portal-filter-${f.toLowerCase()}`}
                            onClick={() => setFilter(f)}
                            variant={filter === f ? "default" : "ghost"}
                            size="sm"
                            className={
                                filter === f
                                    ? "bg-c1b-primary text-white hover:bg-c1b-ink"
                                    : "text-c1b-muted hover:text-c1b-primary"
                            }
                        >
                            {f}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Grid */}
            {loading ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {Array.from({ length: 12 }).map((_, i) => (
                        <div key={i} className="h-32 rounded-2xl shimmer-bg" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="customer-grid">
                    {filtered.map((c, i) => {
                        const tint =
                            c.risk_label === "HIGH" ? "#F43F5E" : c.risk_label === "MEDIUM" ? "#F59E0B" : "#10B981";
                        return (
                            <motion.div
                                key={c.customer_id}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: Math.min(i, 24) * 0.02, duration: 0.3 }}
                                whileHover={{ scale: 1.02 }}
                                data-testid={`customer-card-${c.customer_id}`}
                            >
                                <Link
                                    to={`/customer/${c.customer_id}`}
                                    className="block bg-c1b-card border border-c1b-border rounded-2xl p-4 hover:shadow-lg hover:border-c1b-accent/40 transition-all duration-200 group"
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="font-display font-bold text-lg text-c1b-primary">
                                            {c.customer_id}
                                        </div>
                                        <span
                                            className="w-2.5 h-2.5 rounded-full mt-2 animate-pulse-ring"
                                            style={{ backgroundColor: tint, "--pulse-color": `${tint}55` }}
                                        />
                                    </div>
                                    <RiskBadge label={c.risk_label} />
                                    <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-c1b-border">
                                        <div>
                                            <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Limit</div>
                                            <div className="text-sm font-semibold text-c1b-primary">
                                                ₹{Math.round(c.credit_limit / 1000)}k
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Util</div>
                                            <div className="text-sm font-semibold text-c1b-primary">
                                                {(c.utilization_rate * 100).toFixed(0)}%
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-3 flex items-center justify-between text-[11px]">
                                        <span className="text-c1b-muted">{c.recommended_action}</span>
                                        <ArrowUpRight className="w-3.5 h-3.5 text-c1b-accent opacity-0 group-hover:opacity-100 transition" />
                                    </div>
                                </Link>
                            </motion.div>
                        );
                    })}
                    {filtered.length === 0 && (
                        <div className="col-span-full text-center py-12 text-c1b-muted">No customers match.</div>
                    )}
                </div>
            )}
        </div>
    );
}
