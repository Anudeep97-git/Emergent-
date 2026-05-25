import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { LogOut, Upload, Users, Activity, Bot, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

const NavItem = ({ to, icon: Icon, children }) => (
    <NavLink
        to={to}
        data-testid={`nav-${to.replace("/", "")}`}
        className={({ isActive }) =>
            `group flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                    ? "bg-pn-accent text-white shadow-lg shadow-pn-accent/30"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
            }`
        }
    >
        <Icon className="w-4 h-4" />
        <span>{children}</span>
    </NavLink>
);

export default function DashboardLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const onLogout = async () => {
        await logout();
        navigate("/login");
    };

    return (
        <div className="min-h-screen flex bg-pn-surface">
            {/* Sidebar */}
            <aside className="w-64 shrink-0 bg-pn-primary text-white flex flex-col">
                <div className="px-6 py-6 border-b border-white/10">
                    <Link to="/portal" className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-xl bg-pn-accent flex items-center justify-center shadow-lg shadow-pn-accent/40">
                            <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                            <div className="font-display text-lg font-bold leading-none tracking-tight">Prima Nova</div>
                            <div className="text-[10px] uppercase tracking-[0.18em] text-pn-muted mt-1">
                                Credit Risk
                            </div>
                        </div>
                    </Link>
                </div>
                <nav className="flex-1 p-3 space-y-1">
                    <NavItem to="/portal" icon={Users}>Customer Portal</NavItem>
                    <NavItem to="/upload" icon={Upload}>Upload & Pipeline</NavItem>
                    <NavItem to="/results" icon={Activity}>Risk Results</NavItem>
                    <NavItem to="/agent" icon={Bot}>AI Agent</NavItem>
                </nav>
                <div className="p-3 border-t border-white/10">
                    <div className="px-3 py-2 rounded-lg bg-white/5 mb-2" data-testid="user-banner">
                        <div className="text-sm font-medium truncate">{user?.full_name || user?.email}</div>
                        <div className="text-[11px] uppercase tracking-wider text-pn-muted mt-0.5">
                            {user?.role}
                        </div>
                    </div>
                    <Button
                        data-testid="logout-button"
                        variant="ghost"
                        onClick={onLogout}
                        className="w-full justify-start text-slate-300 hover:bg-white/5 hover:text-white"
                    >
                        <LogOut className="w-4 h-4 mr-2" /> Sign out
                    </Button>
                </div>
            </aside>
            {/* Main */}
            <main className="flex-1 overflow-auto">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="p-8 max-w-[1400px] mx-auto"
                >
                    <Outlet />
                </motion.div>
            </main>
        </div>
    );
}
