import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";

export default function ExportButton({ customerId }) {
    const [busy, setBusy] = useState(false);

    const handle = async () => {
        setBusy(true);
        try {
            const tok = localStorage.getItem("c1b_token");
            const r = await fetch(`${API_BASE}/dashboard/report/${customerId}`, {
                headers: { Authorization: `Bearer ${tok}` },
            });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `c1b_report_${customerId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            toast.success("Report downloaded");
        } catch (e) {
            toast.error(`Export failed: ${e.message}`);
        } finally {
            setBusy(false);
        }
    };

    return (
        <Button
            onClick={handle}
            disabled={busy}
            variant="outline"
            data-testid="export-pdf-button"
            className="border-c1b-accent/30 text-c1b-accent hover:bg-c1b-accent/10 hover:text-c1b-accent hover:scale-[1.02] transition-all"
        >
            {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
            Export PDF
        </Button>
    );
}
