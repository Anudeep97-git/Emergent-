import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle2, History, Pin, RotateCw, TrendingDown, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function MLflowPanel({ user }) {
    const [drift, setDrift] = useState(null);
    const [runs, setRuns] = useState([]);
    const [baseline, setBaseline] = useState(null);
    const [retraining, setRetraining] = useState(false);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        try {
            const [d, r, b] = await Promise.all([
                api.get("/mlflow/drift-check"),
                api.get("/mlflow/runs?limit=8"),
                api.get("/mlflow/baseline"),
            ]);
            setDrift(d.data);
            setRuns(r.data);
            setBaseline(b.data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const pollStatus = async () => {
        for (let i = 0; i < 30; i++) {
            await new Promise((res) => setTimeout(res, 2000));
            const { data } = await api.get("/mlflow/retrain-status");
            if (!data.running) {
                if (data.last_status === "SUCCESS") toast.success("Retrain finished — model registry refreshed");
                else toast.error(`Retrain failed: ${data.last_message?.slice(0, 120)}`);
                setRetraining(false);
                await load();
                return;
            }
        }
        setRetraining(false);
        toast.warning("Retrain still running — refresh later");
    };

    const onRetrain = async () => {
        if (retraining) return;
        setRetraining(true);
        try {
            await api.post("/mlflow/retrain");
            toast.info("Retrain dispatched");
            pollStatus();
        } catch (e) {
            setRetraining(false);
            toast.error(e?.response?.data?.detail || "Retrain failed");
        }
    };

    const onPin = async (runId) => {
        try {
            await api.post(`/mlflow/baseline/${runId}`);
            toast.success("Baseline pinned");
            await load();
        } catch (e) {
            toast.error(e?.response?.data?.detail || "Pin failed");
        }
    };

    const isAdmin = user?.role === "admin";
    const tint = drift?.drift_detected ? "#F43F5E" : "#10B981";

    if (loading) return <div className="h-44 rounded-2xl shimmer-bg" data-testid="mlflow-skeleton" />;

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="bg-pn-card border border-pn-border rounded-2xl p-6"
            data-testid="mlflow-panel"
        >
            <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-1">
                        MLflow Tracking · Phase 10.4
                    </div>
                    <div className="font-display text-xl font-bold text-pn-primary tracking-tight flex items-center gap-2">
                        <Activity className="w-5 h-5 text-pn-accent" />
                        Model Drift Monitor
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div
                        className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5"
                        style={{ backgroundColor: `${tint}1a`, color: tint, border: `1px solid ${tint}55` }}
                        data-testid="mlflow-drift-status"
                    >
                        {drift?.drift_detected ? (
                            <><AlertTriangle className="w-3.5 h-3.5" /> Drift Detected</>
                        ) : (
                            <><CheckCircle2 className="w-3.5 h-3.5" /> Stable</>
                        )}
                    </div>
                    {isAdmin && (
                        <Button
                            onClick={onRetrain}
                            disabled={retraining}
                            data-testid="mlflow-retrain-button"
                            className="bg-pn-accent hover:bg-pn-accent-soft text-white hover:scale-[1.02] transition-all"
                        >
                            {retraining ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RotateCw className="w-4 h-4 mr-2" />}
                            Retrain Model
                        </Button>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <div className="p-3 rounded-xl bg-pn-surface" data-testid="mlflow-baseline-auc">
                    <div className="text-[10px] uppercase tracking-wider text-pn-muted">Baseline AUC</div>
                    <div className="font-mono text-lg font-bold text-pn-primary mt-1">
                        {drift?.baseline_auc?.toFixed(4) ?? "—"}
                    </div>
                </div>
                <div className="p-3 rounded-xl bg-pn-surface" data-testid="mlflow-current-auc">
                    <div className="text-[10px] uppercase tracking-wider text-pn-muted">Current AUC</div>
                    <div className="font-mono text-lg font-bold text-pn-primary mt-1">
                        {drift?.current_auc?.toFixed(4) ?? "—"}
                    </div>
                </div>
                <div className="p-3 rounded-xl bg-pn-surface" data-testid="mlflow-auc-drop">
                    <div className="text-[10px] uppercase tracking-wider text-pn-muted flex items-center gap-1">
                        <TrendingDown className="w-3 h-3" /> AUC Drop
                    </div>
                    <div className="font-mono text-lg font-bold mt-1" style={{ color: tint }}>
                        {drift ? (drift.auc_drop * 100).toFixed(2) + "%" : "—"}
                    </div>
                </div>
                <div className="p-3 rounded-xl bg-pn-surface">
                    <div className="text-[10px] uppercase tracking-wider text-pn-muted">Threshold</div>
                    <div className="font-mono text-lg font-bold text-pn-primary mt-1">
                        {drift?.threshold ? `${drift.threshold * 100}%` : "—"}
                    </div>
                </div>
            </div>

            <p className="text-xs text-pn-muted leading-relaxed mb-4">{drift?.message}</p>

            <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-pn-muted mb-2 flex items-center gap-1">
                    <History className="w-3.5 h-3.5" /> Recent Runs
                </div>
                <div className="border border-pn-border rounded-xl bg-white overflow-hidden">
                    <div className="grid grid-cols-12 px-4 py-2 text-[10px] uppercase tracking-wider text-pn-muted bg-pn-surface border-b border-pn-border">
                        <div className="col-span-4">Run ID</div>
                        <div className="col-span-2">Trigger</div>
                        <div className="col-span-2">AUC</div>
                        <div className="col-span-3">Started</div>
                        <div className="col-span-1 text-right">Pin</div>
                    </div>
                    {runs.map((r, i) => {
                        const isBase = r.run_id === baseline?.run_id;
                        return (
                            <motion.div
                                key={r.run_id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.05, duration: 0.3 }}
                                className={`grid grid-cols-12 px-4 py-2.5 items-center text-xs border-b border-pn-border last:border-b-0 ${isBase ? "bg-pn-accent/5" : ""}`}
                                data-testid={`mlflow-run-${i}`}
                            >
                                <div className="col-span-4 font-mono text-pn-primary truncate flex items-center gap-1.5">
                                    {isBase && <Pin className="w-3 h-3 text-pn-accent" />}
                                    {r.run_id.slice(0, 16)}…
                                </div>
                                <div className="col-span-2 text-pn-muted">{r.trigger}</div>
                                <div className="col-span-2 font-mono font-semibold text-pn-primary">{r.roc_auc.toFixed(4)}</div>
                                <div className="col-span-3 text-pn-muted text-[11px]">
                                    {new Date(r.start_time).toLocaleString()}
                                </div>
                                <div className="col-span-1 text-right">
                                    {isAdmin && !isBase && (
                                        <button
                                            onClick={() => onPin(r.run_id)}
                                            data-testid={`mlflow-pin-${i}`}
                                            className="text-pn-muted hover:text-pn-accent transition"
                                            title="Pin as baseline"
                                        >
                                            <Pin className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>
                            </motion.div>
                        );
                    })}
                    {runs.length === 0 && (
                        <div className="p-4 text-center text-xs text-pn-muted">No runs yet — trigger a retrain.</div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}
