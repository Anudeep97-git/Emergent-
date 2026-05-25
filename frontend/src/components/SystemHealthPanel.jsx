import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings2, ChevronDown } from "lucide-react";
import MLflowPanel from "@/components/MLflowPanel";
import ObservabilityPanel from "@/components/ObservabilityPanel";

/**
 * Collapsed "System Health" container that hides technical operational panels
 * (model lifecycle, alerting, error rates) behind an admin-only toggle.
 * Non-admins don't see this at all.
 */
export default function SystemHealthPanel({ user }) {
    const [open, setOpen] = useState(false);
    if (user?.role !== "admin") return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="bg-pn-card border border-pn-border rounded-2xl overflow-hidden"
            data-testid="system-health-panel"
        >
            <button
                onClick={() => setOpen((v) => !v)}
                data-testid="system-health-toggle"
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-pn-surface transition group"
            >
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-pn-accent/10 text-pn-accent flex items-center justify-center">
                        <Settings2 className="w-4 h-4" />
                    </div>
                    <div className="text-left">
                        <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted">
                            Operations (admin only)
                        </div>
                        <div className="font-display text-base font-bold text-pn-primary tracking-tight">
                            System Health &amp; Model Lifecycle
                        </div>
                    </div>
                </div>
                <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
                    <ChevronDown className="w-5 h-5 text-pn-muted group-hover:text-pn-primary" />
                </motion.div>
            </button>

            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        key="content"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="border-t border-pn-border"
                    >
                        <div className="p-6 space-y-5 bg-pn-surface/50">
                            <MLflowPanel user={user} />
                            <ObservabilityPanel user={user} />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
