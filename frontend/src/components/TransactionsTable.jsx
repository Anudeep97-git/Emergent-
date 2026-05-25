import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, Loader2, ShoppingBag, CreditCard, DollarSign, Banknote, Receipt } from "lucide-react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const TYPE_META = {
    "Purchase":     { tint: "#6366F1", icon: ShoppingBag, sign: -1 },
    "Payment":      { tint: "#10B981", icon: Banknote,    sign: +1 },
    "Credit":       { tint: "#0EA5E9", icon: Receipt,     sign: +1 },
    "Fee":          { tint: "#F43F5E", icon: Receipt,     sign: -1 },
    "Cash Advance": { tint: "#F59E0B", icon: CreditCard,  sign: -1 },
};

const fmtUSD = (v) =>
    `${v < 0 ? "-" : ""}$${Math.abs(Number(v) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function TransactionsTable({ customerId }) {
    const [filter, setFilter] = useState("all");
    const [query, setQuery] = useState("");
    const [debouncedQ, setDebouncedQ] = useState("");
    const [page, setPage] = useState(1);
    const [limit] = useState(10);
    const [data, setData] = useState({ items: [], total: 0 });
    const [types, setTypes] = useState({ types: [], total: 0, total_amount_usd: 0 });
    const [loading, setLoading] = useState(true);

    // Debounce search input
    useEffect(() => {
        const t = setTimeout(() => setDebouncedQ(query.trim()), 300);
        return () => clearTimeout(t);
    }, [query]);

    // Load type summary once per customer
    useEffect(() => {
        (async () => {
            try {
                const { data } = await api.get(`/customer/transactions/${customerId}/types`);
                setTypes(data);
            } catch (_) {}
        })();
    }, [customerId]);

    // Load paginated transactions whenever filter/query/page changes
    useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            try {
                const { data } = await api.get(`/customer/transactions/${customerId}`, {
                    params: { page, limit, tx_type: filter, q: debouncedQ },
                });
                if (alive) setData(data);
            } finally {
                if (alive) setLoading(false);
            }
        })();
        return () => { alive = false; };
    }, [customerId, page, limit, filter, debouncedQ]);

    // Reset to page 1 when filter or query changes
    useEffect(() => { setPage(1); }, [filter, debouncedQ]);

    const totalPages = Math.max(1, Math.ceil((data.total || 0) / limit));
    const filterPills = useMemo(() => [
        { key: "all", label: "All", count: types.total },
        ...(types.types || []).map((t) => ({ key: t.type, label: t.type, count: t.count })),
    ], [types]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.25 }}
            className="bg-pn-card border border-pn-border rounded-2xl p-6"
            data-testid="transactions-table"
        >
            <div className="flex items-end justify-between flex-wrap gap-3 mb-5">
                <div>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-pn-muted">Transactions</div>
                    <div className="font-display text-xl font-bold text-pn-primary tracking-tight">
                        Recent Activity
                    </div>
                    <div className="text-xs text-pn-muted mt-1">
                        <span className="font-mono text-pn-primary">{types.total}</span> transactions ·
                        net <span className="font-mono text-pn-primary">{fmtUSD(types.total_amount_usd)}</span>
                    </div>
                </div>
                <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-pn-muted" />
                    <Input
                        data-testid="tx-search-input"
                        placeholder="Search merchant or description"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="pl-10 h-10 bg-white border-pn-border"
                    />
                </div>
            </div>

            {/* Type filter pills */}
            <div className="flex flex-wrap items-center gap-1.5 mb-4">
                {filterPills.map((p) => {
                    const active = filter === p.key;
                    const tint = p.key === "all" ? "#0F172A" : TYPE_META[p.key]?.tint || "#94A3B8";
                    return (
                        <button
                            key={p.key}
                            data-testid={`tx-filter-${p.key.toLowerCase().replace(/\s/g, "-")}`}
                            onClick={() => setFilter(p.key)}
                            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 border ${
                                active
                                    ? "text-white shadow-sm"
                                    : "text-pn-ink bg-white hover:bg-pn-surface border-pn-border"
                            }`}
                            style={active ? { backgroundColor: tint, borderColor: tint } : undefined}
                        >
                            {p.label}
                            <span className={`ml-1.5 text-[10px] font-mono ${active ? "opacity-80" : "text-pn-muted"}`}>
                                {p.count}
                            </span>
                        </button>
                    );
                })}
            </div>

            {/* Table */}
            <div className="relative overflow-x-auto rounded-xl border border-pn-border">
                <table className="w-full text-sm" data-testid="tx-table">
                    <thead className="bg-pn-surface text-[11px] uppercase tracking-wider text-pn-muted">
                        <tr>
                            <th className="text-left px-4 py-3 font-semibold">Date</th>
                            <th className="text-left px-4 py-3 font-semibold">Type</th>
                            <th className="text-left px-4 py-3 font-semibold">Description</th>
                            <th className="text-right px-4 py-3 font-semibold">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && (
                            <tr>
                                <td colSpan={4} className="text-center py-10">
                                    <Loader2 className="w-5 h-5 animate-spin text-pn-muted inline-block" />
                                </td>
                            </tr>
                        )}
                        {!loading && data.items.length === 0 && (
                            <tr>
                                <td colSpan={4} className="text-center py-10 text-pn-muted text-sm">
                                    No transactions match.
                                </td>
                            </tr>
                        )}
                        {!loading && data.items.map((t, i) => {
                            const meta = TYPE_META[t.transaction_type] || { tint: "#94A3B8", icon: DollarSign, sign: 0 };
                            const Icon = meta.icon;
                            const isCredit = ["Payment", "Credit"].includes(t.transaction_type);
                            const amountColor = isCredit ? "#10B981" : "#1E293B";
                            return (
                                <tr
                                    key={t.reference_number || i}
                                    data-testid={`tx-row-${i}`}
                                    className="border-t border-pn-border hover:bg-pn-surface/60 transition-colors"
                                >
                                    <td className="px-4 py-3 font-mono text-xs text-pn-ink whitespace-nowrap">
                                        {t.trans_date}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span
                                            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-semibold"
                                            style={{
                                                color: meta.tint,
                                                backgroundColor: `${meta.tint}1a`,
                                                border: `1px solid ${meta.tint}33`,
                                            }}
                                        >
                                            <Icon className="w-3 h-3" />
                                            {t.transaction_type}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-pn-ink">
                                        <div className="font-medium leading-tight">{t.description.trim()}</div>
                                        <div className="text-[10px] text-pn-muted font-mono mt-0.5">
                                            ref {t.reference_number?.slice(0, 12)}
                                        </div>
                                    </td>
                                    <td
                                        className="px-4 py-3 text-right font-mono font-semibold tabular-nums"
                                        style={{ color: amountColor }}
                                    >
                                        {fmtUSD(t.amount_usd)}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {data.total > limit && (
                <div className="flex items-center justify-between mt-4 text-xs text-pn-muted">
                    <span>
                        Showing <span className="font-mono text-pn-primary">{(page - 1) * limit + 1}</span>–
                        <span className="font-mono text-pn-primary">{Math.min(page * limit, data.total)}</span> of
                        <span className="font-mono text-pn-primary"> {data.total}</span>
                    </span>
                    <div className="flex items-center gap-1">
                        <Button
                            data-testid="tx-page-prev"
                            variant="ghost"
                            size="sm"
                            disabled={page <= 1}
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            className="h-8"
                        >
                            <ChevronLeft className="w-4 h-4 mr-1" /> Prev
                        </Button>
                        <span className="px-3 font-mono">
                            {page} / {totalPages}
                        </span>
                        <Button
                            data-testid="tx-page-next"
                            variant="ghost"
                            size="sm"
                            disabled={page >= totalPages}
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            className="h-8"
                        >
                            Next <ChevronRight className="w-4 h-4 ml-1" />
                        </Button>
                    </div>
                </div>
            )}
        </motion.div>
    );
}
