import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import RadialGauge from "@/components/RadialGauge";
import RiskBadge from "@/components/RiskBadge";
import SHAPTable from "@/components/SHAPTable";
import CreditDecisionCard from "@/components/CreditDecisionCard";
import ExportButton from "@/components/ExportButton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function RiskResultsPage() {
    const { customerId } = useParams();
    const navigate = useNavigate();
    const [cid, setCid] = useState(customerId || "C001");
    const [decision, setDecision] = useState(null);
    const [loading, setLoading] = useState(false);

    const load = async (id) => {
        setLoading(true);
        try {
            const r = await api.get(`/customer/decision/${id}`);
            setDecision(r.data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load(cid);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [customerId]);

    return (
        <div className="space-y-7">
            <div className="flex items-end justify-between flex-wrap gap-4">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-2">Prima Nova</div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold text-pn-primary tracking-tight">
                        Risk Results
                    </h1>
                    <p className="text-pn-muted mt-2 text-sm max-w-xl">
                        Customer risk score with the top contributing factors driving the decision.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Input
                        data-testid="results-customer-input"
                        value={cid}
                        onChange={(e) => setCid(e.target.value.toUpperCase())}
                        className="w-32 h-10 bg-white border-pn-border font-mono"
                    />
                    <Button
                        data-testid="results-load-button"
                        onClick={() => { navigate(`/results/${cid}`); load(cid); }}
                        className="bg-pn-primary hover:bg-pn-ink hover:scale-[1.02] transition-all"
                    >
                        Load
                    </Button>
                    {decision && <ExportButton customerId={cid} />}
                </div>
            </div>

            {loading || !decision ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                    <div className="h-64 rounded-2xl shimmer-bg" />
                    <div className="lg:col-span-2 h-64 rounded-2xl shimmer-bg" />
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                        <motion.div
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4 }}
                            className="bg-pn-card border border-pn-border rounded-2xl p-6 flex flex-col items-center justify-center"
                        >
                            <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted mb-4">Risk Score</div>
                            <RadialGauge score={decision.risk_score} />
                            <div className="mt-4">
                                <RiskBadge label={decision.risk_label} size="lg" />
                            </div>
                        </motion.div>
                        <div className="lg:col-span-2">
                            <SHAPTable factors={decision.contributing_factors} />
                        </div>
                    </div>
                    <CreditDecisionCard decision={decision} />
                </>
            )}
        </div>
    );
}
