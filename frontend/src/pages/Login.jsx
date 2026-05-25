import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, ShieldCheck, Loader2 } from "lucide-react";
import { useNavigate, Navigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
    const { user, login, loading } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState("admin@primanova.com");
    const [password, setPassword] = useState("admin123");
    const [showPw, setShowPw] = useState(false);
    const [shake, setShake] = useState(0);

    if (user) return <Navigate to="/portal" replace />;

    const submit = async (e) => {
        e.preventDefault();
        try {
            const d = await login(email, password);
            toast.success(`Welcome back, ${d.full_name || d.email}`);
            navigate(d.is_existing_customer ? "/portal" : "/upload");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Invalid credentials");
            setShake((s) => s + 1);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-c1b-primary grid-bg overflow-hidden relative">
            {/* Decorative glow */}
            <div className="absolute top-1/4 left-1/4 w-[480px] h-[480px] rounded-full bg-c1b-accent/20 blur-[120px] pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-[420px] h-[420px] rounded-full bg-emerald-500/15 blur-[140px] pointer-events-none" />

            <AnimatePresence mode="wait">
                <motion.form
                    key={shake}
                    onSubmit={submit}
                    initial={{ y: 40, opacity: 0 }}
                    animate={
                        shake
                            ? { y: 0, opacity: 1, x: [0, -10, 10, -8, 8, -4, 4, 0] }
                            : { y: 0, opacity: 1 }
                    }
                    transition={{ duration: shake ? 0.5 : 0.4, ease: "easeOut" }}
                    className="relative z-10 w-full max-w-md mx-4 p-8 glass rounded-3xl shadow-2xl shadow-black/40"
                    data-testid="login-form"
                >
                    <div className="flex items-center gap-3 mb-7">
                        <div className="w-11 h-11 rounded-2xl bg-c1b-accent flex items-center justify-center shadow-lg shadow-c1b-accent/40">
                            <ShieldCheck className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <div className="font-display text-2xl font-bold leading-none text-c1b-primary tracking-tight">
                                Prima Nova
                            </div>
                            <div className="text-xs uppercase tracking-[0.22em] text-c1b-muted mt-1.5">
                                Credit Risk Console
                            </div>
                        </div>
                    </div>

                    <h1 className="text-3xl font-display font-bold text-c1b-primary mb-1 tracking-tight">
                        Welcome back
                    </h1>
                    <p className="text-sm text-c1b-muted mb-6">
                        Sign in to your credit risk console.
                    </p>

                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="email" className="text-c1b-ink text-sm font-medium">Email</Label>
                            <Input
                                id="email"
                                data-testid="login-email-input"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="mt-1.5 h-11 bg-white/80 border-c1b-border"
                                placeholder="admin@primanova.com"
                                required
                            />
                        </div>
                        <div>
                            <Label htmlFor="password" className="text-c1b-ink text-sm font-medium">Password</Label>
                            <div className="relative mt-1.5">
                                <Input
                                    id="password"
                                    data-testid="login-password-input"
                                    type={showPw ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="h-11 bg-white/80 border-c1b-border pr-10"
                                    required
                                />
                                <button
                                    type="button"
                                    data-testid="login-toggle-password"
                                    onClick={() => setShowPw((s) => !s)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-c1b-muted hover:text-c1b-primary transition-colors"
                                >
                                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>
                    </div>

                    <Button
                        type="submit"
                        data-testid="login-submit-button"
                        disabled={loading}
                        className="w-full mt-7 h-11 bg-c1b-primary hover:bg-c1b-ink text-white font-semibold rounded-xl transition-all duration-200 hover:scale-[1.02] hover:shadow-lg disabled:opacity-60"
                    >
                        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
                    </Button>

                    <div className="mt-6 pt-5 border-t border-c1b-border/60 text-[11px] text-c1b-muted leading-relaxed">
                        <div className="uppercase tracking-[0.18em] font-semibold mb-1.5">Demo Accounts</div>
                        admin@primanova.com / admin123 · analyst@primanova.com / analyst123 · customer@primanova.com / customer123
                    </div>
                </motion.form>
            </AnimatePresence>
        </div>
    );
}
