"""Startup-log smoke tests (CI deploy regression guard).

Asserts that the lifespan startup log line emits the expected mode markers so a
deploy that silently drops PROMETHEUS_MULTIPROC_DIR cannot reach production.
"""
import os
import re
import tempfile
import shutil

import pytest

from tests.conftest import spawn_backend


STARTUP_LINE_RE = re.compile(
    r"C1B Credit Risk Assessment Platform v[\d.]+ ready\. "
    r"Sentry=(?P<sentry>\w+) "
    r"PagerDuty=(?P<pd>\w+) "
    r"Prometheus=(?P<prom>\S+)"
)


def _grep_startup(log_path: str) -> dict:
    with open(log_path, "r") as f:
        content = f.read()
    m = STARTUP_LINE_RE.search(content)
    assert m, f"Startup line not found in log. Tail:\n{content[-1500:]}"
    return m.groupdict()


def test_startup_log_single_process_mode():
    """Default boot (no env var) must report Prometheus=single-process."""
    with spawn_backend() as (port, log_path):
        groups = _grep_startup(log_path)
    assert groups["prom"] == "single-process", f"expected single-process, got {groups['prom']}"
    assert groups["sentry"] in ("ACTIVE", "inactive")
    assert groups["pd"] in ("configured", "inactive")


def test_startup_log_multiproc_mode():
    """With PROMETHEUS_MULTIPROC_DIR set, startup line MUST report Prometheus=multiproc.

    This is the CI deploy regression guard: if anyone removes the env var from the
    Dockerfile / k8s manifest, this test fails and the deploy is blocked.
    """
    mp_dir = tempfile.mkdtemp(prefix="c1b_prom_ci_")
    try:
        with spawn_backend(env_extra={"PROMETHEUS_MULTIPROC_DIR": mp_dir}) as (port, log_path):
            groups = _grep_startup(log_path)
        assert groups["prom"] == "multiproc", (
            f"DEPLOY REGRESSION: expected Prometheus=multiproc, got '{groups['prom']}'. "
            "Check PROMETHEUS_MULTIPROC_DIR is set in Dockerfile / k8s manifest."
        )
    finally:
        shutil.rmtree(mp_dir, ignore_errors=True)


def test_startup_log_contains_sentry_and_pagerduty_fields():
    """Every startup must announce the Sentry + PagerDuty configuration state."""
    with spawn_backend() as (_, log_path):
        groups = _grep_startup(log_path)
    assert groups["sentry"] in ("ACTIVE", "inactive"), "Sentry status missing"
    assert groups["pd"] in ("configured", "inactive"), "PagerDuty status missing"
