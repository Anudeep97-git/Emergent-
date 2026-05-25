import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { BrandingProvider } from "@/lib/branding";
import { Toaster } from "@/components/ui/sonner";
import LoginPage from "@/pages/Login";
import UploadPage from "@/pages/Upload";
import RiskResultsPage from "@/pages/RiskResults";
import CustomerPortalPage from "@/pages/CustomerPortal";
import CustomerDashboardPage from "@/pages/CustomerDashboard";
import AgentChatPage from "@/pages/AgentChat";
import AdminBrandingPage from "@/pages/AdminBranding";
import DashboardLayout from "@/components/layout/DashboardLayout";

const RequireAuth = () => {
    const { user } = useAuth();
    if (!user) return <Navigate to="/login" replace />;
    return <Outlet />;
};

const RequireAdmin = () => {
    const { user } = useAuth();
    if (!user) return <Navigate to="/login" replace />;
    if (user.role !== "admin") return <Navigate to="/portal" replace />;
    return <Outlet />;
};

function App() {
    return (
        <BrandingProvider>
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<LoginPage />} />
                        <Route element={<RequireAuth />}>
                            <Route element={<DashboardLayout />}>
                                <Route path="/" element={<Navigate to="/portal" replace />} />
                                <Route path="/upload" element={<UploadPage />} />
                                <Route path="/results/:customerId?" element={<RiskResultsPage />} />
                                <Route path="/portal" element={<CustomerPortalPage />} />
                                <Route path="/customer/:customerId" element={<CustomerDashboardPage />} />
                                <Route path="/agent" element={<AgentChatPage />} />
                                <Route element={<RequireAdmin />}>
                                    <Route path="/admin/branding" element={<AdminBrandingPage />} />
                                </Route>
                            </Route>
                        </Route>
                        <Route path="*" element={<Navigate to="/portal" replace />} />
                    </Routes>
                </BrowserRouter>
                <Toaster position="top-right" richColors />
            </AuthProvider>
        </BrandingProvider>
    );
}

export default App;
