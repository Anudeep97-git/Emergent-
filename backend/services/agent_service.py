"""AI Agent service — Claude Sonnet 4.5 (Emergent Universal Key) acting as a ReAct
agent with 4 tools that proxy to data_service / ml_service.

Uses emergentintegrations LlmChat. The agent receives a prompt naming the
customer_id; we pre-execute the 4 tools server-side to populate context, then
let the LLM compose a natural-language risk summary in the required format.
"""
import os
import json
import asyncio
from typing import Dict, Any, List

from emergentintegrations.llm.chat import LlmChat, UserMessage

from services import data_service, ml_service
from config import PLATFORM, MODEL_VERSION

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

SYSTEM_PROMPT = f"""You are the C1B Credit Risk AI Agent — a ReAct-style assistant for the
{PLATFORM['name']} ({PLATFORM['version']}). You have access to 4 internal tools whose results
have been pre-fetched and given to you in the user prompt:

  - Phase1_FeatureProfile : customer's engineered 53-feature snapshot
  - Phase2_RiskPredict    : LightGBM risk score + SHAP top-5 drivers
  - Phase3_CreditAction   : APR & credit limit recommendation
  - Phase4_PipelineStatus : nightly batch status / expand-eligibility flag

When you answer a question about a customer's risk, ALWAYS use this exact format on the first line:

"Customer {{id}} is {{RISK_TIER}} RISK ({{prob}}%). Recommended action: {{action}} credit limit from ₹{{current}} to ₹{{new}}. APR {{apr_status}} at {{apr}}%. Top driver: {{top_shap_feature}}."

After that line, you may add 1-3 sentences of supporting context, drawing only on the tool outputs you've been given.
If a question is not about a specific customer, answer concisely using the platform metadata and registry. Never invent data."""


TOOL_DEFS = [
    {"name": "Phase1_FeatureProfile", "desc": "Get the 53-feature engineered profile for a customer_id"},
    {"name": "Phase2_RiskPredict",    "desc": "Get the risk score and bucket for a customer_id"},
    {"name": "Phase3_CreditAction",   "desc": "Get APR and credit-limit recommendation for a customer_id"},
    {"name": "Phase4_PipelineStatus", "desc": "Get batch scoring status and notification flag for a customer_id"},
]


def _run_tools(customer_id: str) -> Dict[str, Any]:
    """Execute the 4 ReAct tools server-side, with simple retry."""
    trace: List[Dict[str, Any]] = []
    feats = data_service.get_customer_features(customer_id) or {}
    trace.append({"tool": "Phase1_FeatureProfile", "ok": bool(feats), "keys": list(feats.keys())[:5]})

    risk: Dict[str, Any] = {}
    last_err = None
    for _ in range(3):
        try:
            risk = ml_service.predict_risk(feats, current_limit=float(feats.get("credit_limit", 100000)))
            break
        except Exception as e:
            last_err = str(e)
    trace.append({"tool": "Phase2_RiskPredict", "ok": bool(risk), "err": last_err})

    action = data_service.get_phase3_action(customer_id) or {}
    trace.append({"tool": "Phase3_CreditAction", "ok": bool(action)})

    batch = data_service.get_phase4_batch_result(customer_id) or {}
    trace.append({"tool": "Phase4_PipelineStatus", "ok": bool(batch)})

    return {"features": feats, "risk": risk, "action": action, "batch": batch, "trace": trace}


def _flag_for_review(risk: Dict[str, Any]) -> bool:
    """Escalation rule: risk_score > 0.98 AND confidence < 60%."""
    try:
        score = float(risk.get("risk_score", 0))
        conf_str = str(risk.get("confidence", "0%")).rstrip("%")
        conf = float(conf_str) / 100.0
        return score > 0.98 and conf < 0.60
    except Exception:
        return False


async def chat(session_id: str, message: str, customer_id: str = None) -> Dict[str, Any]:
    flagged = False
    context_blob: Dict[str, Any] = {"platform": PLATFORM, "model_version": MODEL_VERSION}
    trace: List[Dict[str, Any]] = []
    if customer_id:
        bundle = _run_tools(customer_id)
        context_blob.update(bundle)
        trace = bundle["trace"]
        flagged = _flag_for_review(bundle.get("risk", {}))

    user_prompt = f"""User question: {message}

Customer ID: {customer_id or 'N/A'}

Tool outputs (pre-fetched):
{json.dumps(context_blob, indent=2, default=str)[:6000]}

Compose your answer now."""

    if not EMERGENT_KEY:
        # offline / no-key fallback
        risk = context_blob.get("risk", {})
        action = context_blob.get("action", {})
        if customer_id and risk and action:
            answer = (
                f"Customer {customer_id} is {risk.get('risk_label')} RISK "
                f"({float(risk.get('risk_score', 0)) * 100:.2f}%). Recommended action: "
                f"{action.get('action')} credit limit from ₹{action.get('current_limit'):.0f} "
                f"to ₹{action.get('recommended_limit'):.0f}. "
                f"APR moves to {float(action.get('recommended_apr', 0)) * 100:.2f}%. "
                f"Top driver: {next(iter(risk.get('contributing_factors', {})), 'n/a')}."
            )
        else:
            answer = "Agent offline (no LLM key configured). Please set EMERGENT_LLM_KEY."
        return {"session_id": session_id, "response": answer, "tool_trace": trace, "flagged_for_review": flagged}

    try:
        chat_client = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=session_id,
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        msg = UserMessage(text=user_prompt)
        text = await chat_client.send_message(msg)
        if flagged:
            text += "\n\n⚠️ Flagged for manual analyst review (high-score, low-confidence)."
        return {"session_id": session_id, "response": text, "tool_trace": trace, "flagged_for_review": flagged}
    except Exception as e:
        # graceful fallback to cached assessment
        risk = context_blob.get("risk", {})
        answer = f"Agent temporarily unavailable ({type(e).__name__}). Cached risk: {risk.get('risk_label', 'UNKNOWN')} at {risk.get('risk_score', 0)}."
        return {"session_id": session_id, "response": answer, "tool_trace": trace, "flagged_for_review": flagged}
