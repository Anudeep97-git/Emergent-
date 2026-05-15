"""Observability service — Sentry init + PagerDuty alerts + sliding-window error-rate (PRD §10.4).

Graceful no-op if SENTRY_DSN / PAGERDUTY_INTEGRATION_KEY are unset.
Tracks request status codes in an in-memory deque and fires a PagerDuty incident
when the 5xx rate exceeds 1% over a 5-minute rolling window.
"""
import os
import time
import socket
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

# Optional Sentry import — graceful no-op if not installed
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    _SENTRY_OK = True
except Exception:
    sentry_sdk = None
    _SENTRY_OK = False


# ---------- Config ----------
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
PD_KEY = os.environ.get("PAGERDUTY_INTEGRATION_KEY", "").strip()
ENV_NAME = os.environ.get("ENV_NAME", "preview")
ERR_THRESHOLD = float(os.environ.get("ERROR_RATE_THRESHOLD", "0.01"))   # 1 %
ERR_WINDOW_MIN = float(os.environ.get("ERROR_RATE_WINDOW_MIN", "5"))    # 5 min
PD_ENDPOINT = "https://events.pagerduty.com/v2/enqueue"
SOURCE = f"c1b-backend@{socket.gethostname()}"

_recent: deque = deque(maxlen=5000)
_lock = threading.Lock()
_pd_state: Dict[str, Any] = {
    "last_trigger_at": None,
    "last_resolve_at": None,
    "current_incident_key": None,
    "trigger_count": 0,
    "resolve_count": 0,
    "last_error": None,
}


# ---------- Sentry init ----------
def init_sentry() -> bool:
    """Initialise Sentry if DSN is configured. Returns True if active."""
    if not (_SENTRY_OK and SENTRY_DSN):
        return False
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENV_NAME,
            release="c1b@v1.0.0",
            integrations=[FastApiIntegration(), StarletteIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        return True
    except Exception:
        return False


def is_sentry_active() -> bool:
    return bool(_SENTRY_OK and SENTRY_DSN and sentry_sdk and sentry_sdk.Hub.current.client)


def is_pagerduty_configured() -> bool:
    return bool(PD_KEY)


# ---------- Request recording ----------
def record(status_code: int):
    with _lock:
        _recent.append((time.time(), int(status_code)))


def stats(window_min: Optional[float] = None) -> Dict[str, Any]:
    win = float(window_min or ERR_WINDOW_MIN)
    cutoff = time.time() - win * 60.0
    with _lock:
        entries = [e for e in _recent if e[0] >= cutoff]
    total = len(entries)
    errors = sum(1 for _, sc in entries if sc >= 500)
    rate = (errors / total) if total else 0.0
    return {
        "window_min": win,
        "total_requests": total,
        "error_requests": errors,
        "error_rate": round(rate, 6),
        "threshold": ERR_THRESHOLD,
        "exceeds_threshold": rate > ERR_THRESHOLD and total >= 20,
        "sentry_active": is_sentry_active(),
        "pagerduty_configured": is_pagerduty_configured(),
        "env": ENV_NAME,
    }


# ---------- PagerDuty ----------
def _send_pagerduty(event_action: str, summary: str, severity: str = "error",
                    dedup_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not is_pagerduty_configured():
        return {"sent": False, "skipped": True, "reason": "PAGERDUTY_INTEGRATION_KEY not set"}
    payload = {
        "routing_key": PD_KEY,
        "event_action": event_action,
        "dedup_key": dedup_key or f"c1b-{ENV_NAME}-high-error-rate",
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": SOURCE,
            "component": "fastapi-backend",
            "group": "c1b-credit-risk",
            "class": "error-rate",
            "custom_details": details or {},
        },
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.post(PD_ENDPOINT, json=payload)
        ok = 200 <= r.status_code < 300
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:200]}
        return {"sent": ok, "status": r.status_code, "response": body}
    except Exception as e:
        _pd_state["last_error"] = f"{type(e).__name__}: {e}"
        return {"sent": False, "error": str(e)}


def trigger_incident(summary: str, details: Optional[Dict[str, Any]] = None, severity: str = "error") -> Dict[str, Any]:
    dedup = f"c1b-{ENV_NAME}-high-error-rate"
    out = _send_pagerduty("trigger", summary, severity=severity, dedup_key=dedup, details=details)
    if out.get("sent"):
        _pd_state["last_trigger_at"] = datetime.now(timezone.utc).isoformat()
        _pd_state["current_incident_key"] = dedup
        _pd_state["trigger_count"] += 1
    elif out.get("skipped"):
        # mark a "pseudo-open" incident in no-op mode so subsequent checks return ALREADY_OPEN
        _pd_state["current_incident_key"] = dedup + "-noop"
    return out


def resolve_incident(summary: str = "Error rate returned below threshold") -> Dict[str, Any]:
    open_key = _pd_state.get("current_incident_key")
    if not open_key:
        return {"sent": False, "skipped": True, "reason": "no open incident"}
    # If incident is a no-op pseudo-key, just clear locally
    if open_key.endswith("-noop"):
        _pd_state["current_incident_key"] = None
        return {"sent": False, "skipped": True, "reason": "no-op mode (no PD key)", "cleared_local": True}
    out = _send_pagerduty("resolve", summary, dedup_key=open_key)
    if out.get("sent"):
        _pd_state["last_resolve_at"] = datetime.now(timezone.utc).isoformat()
        _pd_state["current_incident_key"] = None
        _pd_state["resolve_count"] += 1
    return out


def check_and_alert() -> Dict[str, Any]:
    """Compute current error rate; trigger PD if > threshold; resolve if back below."""
    s = stats()
    is_open = bool(_pd_state.get("current_incident_key"))
    if s["exceeds_threshold"]:
        if not is_open:
            pd = trigger_incident(
                summary=f"C1B error rate {s['error_rate']*100:.2f}% > {ERR_THRESHOLD*100:.2f}% threshold",
                details=s, severity="error",
            )
            s["pagerduty_action"] = "TRIGGERED"
            s["pagerduty_response"] = pd
        else:
            s["pagerduty_action"] = "ALREADY_OPEN"
    else:
        if is_open:
            pd = resolve_incident()
            s["pagerduty_action"] = "RESOLVED"
            s["pagerduty_response"] = pd
        else:
            s["pagerduty_action"] = "NO_ACTION"
    return s


def state() -> Dict[str, Any]:
    return dict(_pd_state)


def capture_exception(err: Exception, context: Optional[Dict[str, Any]] = None):
    """Manual Sentry capture (no-op if Sentry inactive)."""
    if not is_sentry_active():
        return False
    try:
        if context:
            with sentry_sdk.push_scope() as scope:
                for k, v in context.items():
                    scope.set_extra(k, v)
                sentry_sdk.capture_exception(err)
        else:
            sentry_sdk.capture_exception(err)
        return True
    except Exception:
        return False
