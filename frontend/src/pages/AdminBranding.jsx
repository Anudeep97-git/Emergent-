import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Palette, RotateCcw, Save, Loader2, Eye, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useBranding } from "@/lib/branding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const FIELDS = [
    { key: "app_name", label: "App Name", placeholder: "Prima Nova", type: "text" },
    { key: "app_tagline", label: "Tagline", placeholder: "Credit Risk Console", type: "text" },
    { key: "logo_initials", label: "Logo Initials", placeholder: "PN", type: "text", maxLength: 4 },
    { key: "support_email", label: "Support Email", placeholder: "support@primanova.com", type: "email" },
];

const COLOR_FIELDS = [
    { key: "primary_color", label: "Primary", hint: "Sidebar & headers" },
    { key: "accent_color", label: "Accent", hint: "Buttons & active nav" },
    { key: "success_color", label: "Success", hint: "Approved states" },
    { key: "warning_color", label: "Warning", hint: "Watch states" },
    { key: "danger_color", label: "Danger", hint: "High-risk states" },
];

const HEX_RE = /^#[0-9A-Fa-f]{6}$/;

export default function AdminBrandingPage() {
    const { branding, update, reset, loading } = useBranding();
    const [form, setForm] = useState(branding);
    const [saving, setSaving] = useState(false);
    const [resetting, setResetting] = useState(false);

    useEffect(() => { setForm(branding); }, [branding]);

    const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

    const dirty = Object.keys(form).some((k) => form[k] !== branding[k]);

    const onSave = async () => {
        // Validate hex colors
        for (const f of COLOR_FIELDS) {
            if (form[f.key] && !HEX_RE.test(form[f.key])) {
                toast.error(`${f.label} must be a valid hex color (e.g. #6366F1)`);
                return;
            }
        }
        setSaving(true);
        try {
            await update(form);
            toast.success("Branding updated. Changes are live across the app.");
        } catch (e) {
            toast.error(e?.response?.data?.detail || "Failed to update branding");
        } finally {
            setSaving(false);
        }
    };

    const onReset = async () => {
        if (!window.confirm("Reset all branding fields to Prima Nova defaults?")) return;
        setResetting(true);
        try {
            await reset();
            toast.success("Branding reset to defaults.");
        } catch (e) {
            toast.error(e?.response?.data?.detail || "Failed to reset branding");
        } finally {
            setResetting(false);
        }
    };

    return (
        <div className="space-y-6" data-testid="admin-branding-page">
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl bg-pn-accent flex items-center justify-center shadow-lg shadow-pn-accent/30">
                        <Palette className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-display font-bold text-pn-primary tracking-tight">
                            Branding
                        </h1>
                        <p className="text-sm text-pn-muted">
                            White-label your console. Changes apply instantly across all users.
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        onClick={onReset}
                        disabled={resetting || loading}
                        data-testid="branding-reset-button"
                    >
                        {resetting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
                        Reset
                    </Button>
                    <Button
                        onClick={onSave}
                        disabled={saving || loading || !dirty}
                        className="bg-pn-primary hover:bg-pn-ink text-white"
                        data-testid="branding-save-button"
                    >
                        {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        Save changes
                    </Button>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Identity */}
                <Card className="lg:col-span-2" data-testid="branding-identity-card">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-pn-primary">
                            <ShieldCheck className="w-4 h-4" /> Identity
                        </CardTitle>
                        <CardDescription>Name, tagline, initials shown on the sidebar and login.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {FIELDS.map((f) => (
                            <div key={f.key}>
                                <Label htmlFor={f.key} className="text-pn-ink text-sm font-medium">
                                    {f.label}
                                </Label>
                                <Input
                                    id={f.key}
                                    data-testid={`branding-input-${f.key}`}
                                    type={f.type}
                                    maxLength={f.maxLength}
                                    value={form[f.key] || ""}
                                    placeholder={f.placeholder}
                                    onChange={(e) => setField(f.key, e.target.value)}
                                    className="mt-1.5 h-10"
                                />
                            </div>
                        ))}
                    </CardContent>
                </Card>

                {/* Live Preview */}
                <Card data-testid="branding-preview-card">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-pn-primary">
                            <Eye className="w-4 h-4" /> Live Preview
                        </CardTitle>
                        <CardDescription>How it appears in the sidebar.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-xl bg-pn-primary p-5 text-white">
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold tracking-wider shadow-lg"
                                    style={{ backgroundColor: form.accent_color }}
                                >
                                    {form.logo_initials || "PN"}
                                </div>
                                <div>
                                    <div className="font-display text-base font-bold leading-none tracking-tight">
                                        {form.app_name || "Prima Nova"}
                                    </div>
                                    <div className="text-[10px] uppercase tracking-[0.18em] text-slate-300 mt-1">
                                        {form.app_tagline || "Credit Risk Console"}
                                    </div>
                                </div>
                            </div>
                            <Separator className="my-4 bg-white/10" />
                            <div className="flex flex-wrap gap-2">
                                {COLOR_FIELDS.map((c) => (
                                    <div key={c.key} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                                        <span
                                            className="w-3 h-3 rounded-sm ring-1 ring-white/20"
                                            style={{ backgroundColor: form[c.key] }}
                                        />
                                        {c.label}
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="mt-4 text-[11px] text-pn-muted leading-relaxed">
                            Saved by: <span className="font-mono">{branding.updated_by || "system"}</span>
                            {branding.updated_at && (
                                <> · <span className="font-mono">{new Date(branding.updated_at).toLocaleString()}</span></>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Colors */}
            <Card data-testid="branding-colors-card">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-pn-primary">
                        <Palette className="w-4 h-4" /> Theme Colors
                    </CardTitle>
                    <CardDescription>Use 6-digit hex values. Changes apply across the entire app.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                        {COLOR_FIELDS.map((f) => (
                            <div key={f.key}>
                                <Label htmlFor={f.key} className="text-pn-ink text-sm font-medium">
                                    {f.label}
                                </Label>
                                <div className="text-[11px] text-pn-muted mb-1.5">{f.hint}</div>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="color"
                                        data-testid={`branding-color-picker-${f.key}`}
                                        value={form[f.key] || "#000000"}
                                        onChange={(e) => setField(f.key, e.target.value.toUpperCase())}
                                        className="w-10 h-10 rounded-md border border-pn-border cursor-pointer bg-transparent"
                                    />
                                    <Input
                                        id={f.key}
                                        data-testid={`branding-color-input-${f.key}`}
                                        value={form[f.key] || ""}
                                        onChange={(e) => setField(f.key, e.target.value)}
                                        placeholder="#6366F1"
                                        className="h-10 font-mono text-sm uppercase"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
