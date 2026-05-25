import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload as UploadIcon, FileCheck, CheckCircle2, XCircle, Loader2, Cog, FlaskConical, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";

const STEPS = [
    { key: "ingest",   label: "Ingest",   icon: UploadIcon, desc: "Upload + parse rows" },
    { key: "validate", label: "Validate", icon: FileCheck,  desc: "Schema + null checks" },
    { key: "features", label: "Features", icon: Cog,        desc: "Build 53-feature vector" },
    { key: "score",    label: "Risk Score",    icon: Sparkles,   desc: "Risk scoring & explanations" },
];

export default function UploadPage() {
    const [drag, setDrag] = useState(false);
    const [file, setFile] = useState(null);
    const [fileId, setFileId] = useState(null);
    const [step, setStep] = useState(-1); // current step index (-1 idle, 4 done)
    const [validation, setValidation] = useState(null);
    const [score, setScore] = useState(null);
    const [busy, setBusy] = useState(false);

    const onDrop = (e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f) setFile(f);
    };

    const onSelect = (e) => {
        const f = e.target.files?.[0];
        if (f) setFile(f);
    };

    const runIngest = async () => {
        if (!file) return;
        setBusy(true);
        setStep(0);
        try {
            const fd = new FormData();
            fd.append("file", file);
            const tok = localStorage.getItem("prima_token") || localStorage.getItem("c1b_token");
            const r = await fetch(`${API_BASE}/pipeline/ingest`, {
                method: "POST",
                headers: { Authorization: `Bearer ${tok}` },
                body: fd,
            });
            const data = await r.json();
            if (!r.ok) throw new Error(data?.detail || "Ingest failed");
            setFileId(data.file_id);
            toast.success(`Ingested ${data.rows_detected} rows`);
            setStep(1);

            // Validate
            const v = await api.post(`/pipeline/validate?file_id=${data.file_id}`);
            setValidation(v.data);
            if (!v.data.is_valid) {
                toast.error(`Validation failed: ${v.data.errors.length} errors`);
                return;
            }
            setStep(2);

            // Features (use C001 as illustration since uploaded file may not have customer features yet)
            const feat = await api.post("/pipeline/features?customer_id=C001");
            setStep(3);

            // Score
            const s = await api.post("/pipeline/score", {
                customer_id: "C001",
                feature_vector: feat.data.features,
            });
            setScore(s.data);
            setStep(4);
            toast.success(`Scored ${s.data.customer_id}: ${s.data.risk_label}`);
        } catch (e) {
            toast.error(`Pipeline error: ${e.message || e}`);
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="space-y-7">
            <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-2">Prima Nova</div>
                <h1 className="font-display text-4xl sm:text-5xl font-bold text-pn-primary tracking-tight">
                    Transaction Upload & Scoring
                </h1>
                <p className="text-pn-muted mt-2 text-sm max-w-2xl">
                    Drop a CSV / XLSX / JSON containing your customer transactions. The pipeline ingests, validates,
                    builds risk features, and produces a risk score with the top contributing factors.
                </p>
            </div>

            {/* Drag-drop zone */}
            <motion.div
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={onDrop}
                animate={{ borderColor: drag ? "#6366F1" : "#E2E8F0", backgroundColor: drag ? "rgba(99,102,241,0.04)" : "#fff" }}
                className="border-2 border-dashed rounded-2xl p-10 text-center transition"
                data-testid="dragdrop-zone"
            >
                <UploadIcon className="w-10 h-10 text-pn-accent mx-auto mb-3" />
                <div className="font-display text-xl font-bold text-pn-primary">
                    {file ? file.name : "Drag & drop your transactions file"}
                </div>
                <div className="text-sm text-pn-muted mt-1">Accepted: .csv, .xlsx, .json (max 50MB)</div>
                <div className="mt-5 flex items-center justify-center gap-3">
                    <label htmlFor="fileSelect" className="cursor-pointer">
                        <input id="fileSelect" data-testid="file-input" type="file" className="hidden" accept=".csv,.xlsx,.json" onChange={onSelect} />
                        <span className="inline-block px-4 py-2 rounded-xl bg-white border border-pn-border text-sm font-medium hover:bg-pn-surface transition">
                            Browse file
                        </span>
                    </label>
                    <Button
                        onClick={runIngest}
                        disabled={!file || busy}
                        data-testid="run-pipeline-button"
                        className="bg-pn-primary hover:bg-pn-ink text-white px-5 hover:scale-[1.02] transition-all"
                    >
                        {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <FlaskConical className="w-4 h-4 mr-2" />}
                        Run pipeline
                    </Button>
                </div>
            </motion.div>

            {/* Pipeline progress tracker */}
            <div className="bg-pn-card border border-pn-border rounded-2xl p-6" data-testid="pipeline-progress">
                <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-4">
                    Pipeline Progress
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    {STEPS.map((s, i) => {
                        const done = step > i || step === 4;
                        const active = step === i && busy;
                        const tint = done ? "#10B981" : active ? "#6366F1" : "#94A3B8";
                        const Icon = s.icon;
                        return (
                            <motion.div
                                key={s.key}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.08, duration: 0.3 }}
                                className="p-4 rounded-xl border"
                                style={{ borderColor: `${tint}55`, backgroundColor: `${tint}0d` }}
                                data-testid={`pipeline-step-${s.key}`}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${tint}22`, color: tint }}>
                                        {active ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
                                    </div>
                                    <div className="font-semibold text-pn-primary">{s.label}</div>
                                </div>
                                <div className="text-xs text-pn-muted">{s.desc}</div>
                            </motion.div>
                        );
                    })}
                </div>
            </div>

            {/* Validation result */}
            <AnimatePresence>
                {validation && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="bg-pn-card border border-pn-border rounded-2xl p-6"
                        data-testid="validation-status"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted">Validation</div>
                                <div className="font-display text-xl font-bold text-pn-primary">
                                    {validation.is_valid ? "All schema checks passed" : `${validation.errors.length} errors`}
                                </div>
                            </div>
                            {validation.is_valid ? (
                                <CheckCircle2 className="w-7 h-7 text-pn-success" />
                            ) : (
                                <XCircle className="w-7 h-7 text-pn-danger" />
                            )}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            {Object.entries(validation.column_checks).map(([col, ok]) => (
                                <div
                                    key={col}
                                    className="flex items-center gap-1.5 text-xs px-2 py-1.5 rounded-lg border"
                                    style={{
                                        borderColor: ok ? "#10B98144" : "#F43F5E44",
                                        color: ok ? "#10B981" : "#F43F5E",
                                        backgroundColor: ok ? "#10B9810d" : "#F43F5E0d",
                                    }}
                                >
                                    {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                    <span className="truncate font-mono">{col}</span>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Score result preview link */}
            {score && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-pn-primary text-white rounded-2xl p-6 flex items-center justify-between"
                    data-testid="score-result-banner"
                >
                    <div>
                        <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-1">
                            Sample Score · {score.customer_id}
                        </div>
                        <div className="font-display text-2xl font-bold">
                            {score.risk_label} · {(score.risk_score * 100).toFixed(2)}%
                        </div>
                        <div className="text-xs text-slate-300 mt-1">Confidence {score.confidence} · {score.recommended_action}</div>
                    </div>
                    <Button asChild className="bg-white text-pn-primary hover:bg-slate-100 hover:scale-[1.02] transition-all">
                        <a href={`/customer/${score.customer_id}`} data-testid="score-view-customer-link">View Customer Dashboard →</a>
                    </Button>
                </motion.div>
            )}
        </div>
    );
}
