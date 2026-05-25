import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Loader2, AlertTriangle, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const SESSION_ID = `c1b-ui-${Math.random().toString(36).slice(2, 10)}`;

const SUGGESTIONS = [
    "Assess risk for C031",
    "What is the recommended APR change for C007?",
    "Why is C012 in the high-risk bucket?",
    "Show batch status for C001",
];

export default function AgentChatPage() {
    const [messages, setMessages] = useState([
        {
            role: "assistant",
            text:
                "Hi — I'm your credit risk assistant. Ask me about any customer's risk, recommended credit limit, or APR change (customers C001 – C100).",
        },
    ]);
    const [customerId, setCustomerId] = useState("C001");
    const [input, setInput] = useState("");
    const [busy, setBusy] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const send = async (text) => {
        if (!text.trim() || busy) return;
        setBusy(true);
        setMessages((m) => [...m, { role: "user", text }]);
        setInput("");
        try {
            const r = await api.post("/agent/chat", { session_id: SESSION_ID, message: text, customer_id: customerId });
            setMessages((m) => [
                ...m,
                {
                    role: "assistant",
                    text: r.data.response,
                    trace: r.data.tool_trace,
                    flagged: r.data.flagged_for_review,
                },
            ]);
        } catch (e) {
            toast.error("Agent error");
            setMessages((m) => [
                ...m,
                { role: "assistant", text: `Agent error: ${e?.response?.data?.detail || e.message}` },
            ]);
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="space-y-5">
            <div className="flex items-end justify-between flex-wrap gap-4">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-c1b-muted mb-2">Prima Nova</div>
                    <h1 className="font-display text-4xl sm:text-5xl font-bold text-c1b-primary tracking-tight">
                        Credit Risk Agent
                    </h1>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-c1b-muted uppercase tracking-wider">Customer</span>
                    <Input
                        data-testid="agent-customer-id"
                        value={customerId}
                        onChange={(e) => setCustomerId(e.target.value.toUpperCase())}
                        className="w-28 h-10 bg-white border-c1b-border font-mono"
                    />
                </div>
            </div>

            {/* Chat panel */}
            <div className="bg-c1b-card border border-c1b-border rounded-2xl flex flex-col h-[60vh]" data-testid="agent-chat-panel">
                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                    <AnimatePresence>
                        {messages.map((m, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.3 }}
                                className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}
                                data-testid={`agent-message-${i}`}
                            >
                                <div
                                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                                        m.role === "user" ? "bg-c1b-primary text-white" : "bg-c1b-accent/10 text-c1b-accent"
                                    }`}
                                >
                                    {m.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                </div>
                                <div
                                    className={`max-w-[78%] px-4 py-3 rounded-2xl ${
                                        m.role === "user"
                                            ? "bg-c1b-primary text-white"
                                            : "bg-c1b-surface text-c1b-ink border border-c1b-border"
                                    }`}
                                >
                                    <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.text}</div>
                                    {m.flagged && (
                                        <div className="mt-2 flex items-center gap-1.5 text-xs text-c1b-warning font-semibold">
                                            <AlertTriangle className="w-3.5 h-3.5" /> Flagged for analyst review
                                        </div>
                                    )}
                                    {m.trace && m.trace.length > 0 && (
                                        <div className="mt-2 text-[10px] uppercase tracking-wider text-c1b-muted">
                                            Tools called: {m.trace.map((t) => t.tool).join(" · ")}
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    {busy && (
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-xl bg-c1b-accent/10 text-c1b-accent flex items-center justify-center">
                                <Loader2 className="w-4 h-4 animate-spin" />
                            </div>
                            <div className="px-4 py-3 rounded-2xl bg-c1b-surface border border-c1b-border text-sm text-c1b-muted">
                                Calling tools and composing answer…
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t border-c1b-border">
                    <div className="flex flex-wrap gap-2 mb-3">
                        {SUGGESTIONS.map((s) => (
                            <button
                                key={s}
                                onClick={() => send(s)}
                                disabled={busy}
                                data-testid={`agent-suggest-${s.slice(0, 12)}`}
                                className="text-xs px-3 py-1.5 rounded-full border border-c1b-border bg-white text-c1b-muted hover:text-c1b-accent hover:border-c1b-accent/40 transition"
                            >
                                <Sparkles className="w-3 h-3 inline -mt-0.5 mr-1" />
                                {s}
                            </button>
                        ))}
                    </div>
                    <form
                        onSubmit={(e) => { e.preventDefault(); send(input); }}
                        className="flex items-center gap-2"
                    >
                        <Input
                            data-testid="agent-input"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about a customer's risk, APR, limit decision…"
                            className="bg-white border-c1b-border h-11"
                        />
                        <Button
                            type="submit"
                            disabled={busy || !input.trim()}
                            data-testid="agent-send-button"
                            className="bg-c1b-accent hover:bg-c1b-accent-soft text-white h-11 px-5 hover:scale-[1.02] transition-all"
                        >
                            <Send className="w-4 h-4" />
                        </Button>
                    </form>
                </div>
            </div>
        </div>
    );
}
