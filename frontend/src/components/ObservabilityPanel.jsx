import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldAlert, Siren, Bell, Activity, CheckCircle2, XCircle, Loader2, Play } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function ObservabilityPanel({ user }) {
    const [stats, setStats] = useState(null);
    const [state, setState] = useState(null);
    const [busy, setBusy] = useState(false);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        try {
            const { data } = await api.get("/observability/state");
            setStats(data);
            setState(data.pagerduty_state);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        const t = setInterval(load, 15000);
        return () => clearInterval(t);
    }, []);

    const onCheck = async () => {
        setBusy(true);
        try {
            const { data } = await api.post("/observability/check");
            if (data.pagerduty_action === "TRIGGERED") toast.warning("PagerDuty triggered");
            else if (data.pagerduty_action === "RESOLVED") toast.success("PagerDuty resolved");
            else toast.info(`Check: ${data.pagerduty_action || "no-op"}`);
            await load();
        } catch (e) {
            toast.error(e?.response?.data?.detail || "Check failed");
        } finally { setBusy(false); }
    };

    const onTestAlert = async () => {
        setBusy(true);
        try {
            const { data } = await api.post("/observability/test-alert");
            if (data.sent) toast.success("Test incident dispatched to PagerDuty");
            else toast.warning(data.reason || "PD key not configured — test no-op");
            await load();
        } catch (e) {
            toast.error(e?.response?.data?.detail || "Test failed");
        } finally { setBusy(false); }
    };

    const onTestResolve = async () => {
        setBusy(true);
        try {
            const { data } = await api.post("/observability/test-resolve");
            toast.info(data.sent ? "Incident resolved" : (data.reason || "no open incident"));
            await load();
        } catch (_) {} finally { setBusy(false); }
    };

    if (loading) return <div className="h-44 rounded-2xl shimmer-bg" data-testid="observability-skeleton" />;
    if (!stats) return null;

    const rate = stats.error_rate * 100;
    const exceeds = stats.exceeds_threshold;
    const tint = exceeds ? "#F43F5E" : "#10B981";
    const isAdmin = user?.role === "admin";

    const cfgBadge = (active, label) => (
        <div
            className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5"
            style={{
                backgroundColor: active ? "#10B9811a" : "#94A3B81a",
                color: active ? "#10B981" : "#94A3B8",
                border: `1px solid ${active ? "#10B98155" : "#94A3B855"}`,
            }}
        >
            {active ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {label}
        </div>
    );

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="bg-c1b-card border border-c1b-border rounded-2xl p-6"
            data-testid="observability-panel"
        >
            <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-c1b-muted mb-1">
                        Observability · PRD §10.4
                    </div>
                    <div className="font-display text-xl font-bold text-c1b-primary tracking-tight flex items-center gap-2">
                        <ShieldAlert className="w-5 h-5 text-c1b-accent" />
                        Error Rate & Alerting
                    </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap" data-testid="observability-config">
                    {cfgBadge(stats.sentry_active, "Sentry")}
                    {cfgBadge(stats.pagerduty_configured, "PagerDuty")}
                    <a
                        href="/api/metrics/"
                        target="_blank"
                        rel="noreferrer"
                        data-testid="observability-prometheus-link"
                        className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 bg-c1b-accent/10 text-c1b-accent border border-c1b-accent/30 hover:bg-c1b-accent/20 transition"
                    >
                        <CheckCircle2 className="w-3 h-3" />
                        Prometheus /metrics
                    </a>
                    <div
                        className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5"
                        style={{ backgroundColor: `${tint}1a`, color: tint, border: `1px solid ${tint}55` }}
                        data-testid="observability-status"
                    >
                        {exceeds ? <><Siren className="w-3.5 h-3.5" /> Above Threshold</> : <><Activity className="w-3.5 h-3.5" /> Healthy</>}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <div className="p-3 rounded-xl bg-c1b-surface" data-testid="observability-rate">
                    <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Error Rate</div>
                    <div className="font-mono text-lg font-bold mt-1" style={{ color: tint }}>{rate.toFixed(3)}%</div>
                </div>
                <div className="p-3 rounded-xl bg-c1b-surface">
                    <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Window</div>
                    <div className="font-mono text-lg font-bold text-c1b-primary mt-1">{stats.window_min} min</div>
                </div>
                <div className="p-3 rounded-xl bg-c1b-surface">
                    <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Requests / Errors</div>
                    <div className="font-mono text-lg font-bold text-c1b-primary mt-1">
                        {stats.total_requests} <span className="text-c1b-muted">/</span>{" "}
                        <span className="text-c1b-danger">{stats.error_requests}</span>
                    </div>
                </div>
                <div className="p-3 rounded-xl bg-c1b-surface">
                    <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Threshold</div>
                    <div className="font-mono text-lg font-bold text-c1b-primary mt-1">{(stats.threshold * 100).toFixed(2)}%</div>
                </div>
            </div>

            {state && (state.trigger_count > 0 || state.resolve_count > 0) && (
                <div className="p-3 rounded-xl bg-c1b-surface mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                        <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Triggers</div>
                        <div className="font-semibold text-c1b-danger">{state.trigger_count}</div>
                    </div>
                    <div>
                        <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Resolves</div>
                        <div className="font-semibold text-c1b-success">{state.resolve_count}</div>
                    </div>
                    <div>
                        <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Last Trigger</div>
                        <div className="font-mono text-[11px] text-c1b-primary">
                            {state.last_trigger_at ? new Date(state.last_trigger_at).toLocaleTimeString() : "—"}
                        </div>
                    </div>
                    <div>
                        <div className="text-[10px] uppercase tracking-wider text-c1b-muted">Open Incident</div>
                        <div className="font-mono text-[11px] text-c1b-primary truncate">{state.current_incident_key || "none"}</div>
                    </div>
                </div>
            )}

            {!stats.sentry_active && !stats.pagerduty_configured && (
                <p className="text-xs text-c1b-muted leading-relaxed mb-4">
                    Sentry &amp; PagerDuty are <span className="font-semibold text-c1b-warning">no-op</span> until you set
                    <code className="font-mono text-c1b-primary mx-1 px-1.5 py-0.5 rounded bg-c1b-surface">SENTRY_DSN</code>
                    and
                    <code className="font-mono text-c1b-primary mx-1 px-1.5 py-0.5 rounded bg-c1b-surface">PAGERDUTY_INTEGRATION_KEY</code>
                    in <code className="font-mono text-c1b-primary mx-1 px-1.5 py-0.5 rounded bg-c1b-surface">/app/backend/.env</code>.
                </p>
            )}

            {isAdmin && (
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        onClick={onCheck}
                        disabled={busy}
                        data-testid="observability-check-button"
                        className="bg-c1b-primary hover:bg-c1b-ink text-white hover:scale-[1.02] transition-all"
                    >
                        {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Activity className="w-4 h-4 mr-2" />}
                        Run Drift Check
                    </Button>
                    <Button
                        onClick={onTestAlert}
                        disabled={busy}
                        variant="outline"
                        data-testid="observability-test-alert"
                        className="border-c1b-danger/30 text-c1b-danger hover:bg-c1b-danger/10 hover:text-c1b-danger hover:scale-[1.02] transition-all"
                    >
                        <Bell className="w-4 h-4 mr-2" /> Fire Test Alert
                    </Button>
                    {state?.current_incident_key && (
                        <Button
                            onClick={onTestResolve}
                            disabled={busy}
                            variant="outline"
                            data-testid="observability-test-resolve"
                            className="border-c1b-success/30 text-c1b-success hover:bg-c1b-success/10 hover:text-c1b-success hover:scale-[1.02] transition-all"
                        >
                            <Play className="w-4 h-4 mr-2 rotate-180" /> Resolve Incident
                        </Button>
                    )}
                </div>
            )}
        </motion.div>
    );
}
