/**
 * Maps raw ML feature names → business-friendly labels for the UI.
 * Falls back to a Title-Cased version of the raw key when no mapping exists.
 */
const LABEL_MAP = {
    bureau_score: "Credit Bureau Score",
    bureau_score_6m_avg: "Bureau Score (6-Month Avg)",
    bureau_score_deviation: "Bureau Score Change",
    utilization_rate: "Credit Utilization",
    utilization_volatility_3m: "Utilization Swings (3-Month)",
    utilization_volatility_6m: "Utilization Swings (6-Month)",
    delinquency_status: "Past-Due Status",
    days_past_due: "Days Past Due",
    payment_on_time_flag: "On-Time Payment",
    payment_on_time_avg_3m: "On-Time Rate (3-Month)",
    payment_on_time_avg_6m: "On-Time Rate (6-Month)",
    payment_amount: "Last Payment",
    payment_to_balance: "Payment vs Balance",
    purchases_amount: "Purchase Spend",
    purchases_to_limit: "Spend vs Limit",
    cash_advances: "Cash Advances",
    cash_advance_to_purchase_ratio: "Cash Advance Ratio",
    interest_charged: "Interest Charged",
    fees_charged: "Fees Charged",
    fees_to_balance: "Fees vs Balance",
    interest_to_balance: "Interest vs Balance",
    new_balance: "Closing Balance",
    current_balance: "Current Balance",
    balance_to_limit: "Balance vs Limit",
    credit_limit: "Credit Limit",
    income: "Income",
    income_to_limit: "Income vs Limit",
    age: "Age",
    age_bucket: "Age Group",
    employment_status_enc: "Employment Status",
    geography_region_enc: "Region",
    high_util_flag: "High Utilization Flag",
    dpd_flag: "Delinquency Flag",
    month_idx: "Statement Month",
    trans_count: "Statement Count",
    spend_last_30_days: "Spend (Last 30 Days)",
    spend_mom_change: "Spend Change (Month-on-Month)",
    total_spend: "Total Spend",
    total_purchase_amount: "Total Purchases",
    normalized_purchase_frequency: "Purchase Frequency",
    previous_balance: "Previous Balance",
};

const titleCase = (s) =>
    s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const featureLabel = (raw) => {
    if (!raw) return "";
    // strip common technical suffixes
    const key = String(raw).trim();
    if (LABEL_MAP[key]) return LABEL_MAP[key];
    // lag features: utilization_lag_3m → "Utilization (3 Months Ago)"
    const lag = key.match(/^([a-z_]+?)_lag_(\d+)m$/);
    if (lag) {
        const base = LABEL_MAP[lag[1]] || titleCase(lag[1]);
        return `${base} (${lag[2]} Months Ago)`;
    }
    return titleCase(key);
};
