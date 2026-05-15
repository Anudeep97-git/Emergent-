"""Prometheus multiprocess bootstrap.

When `PROMETHEUS_MULTIPROC_DIR` is set, the prometheus_client switches to a
shared-memory-file backend so metric values aggregate across workers. This
module:

  * creates the directory if missing
  * clears stale .db files from previous boots (per prometheus_client docs)
  * registers a worker-death hook so a dying worker's files are reaped

Safe no-op when `PROMETHEUS_MULTIPROC_DIR` is unset (single-process mode).
"""
import os
import glob
import atexit
import signal
import logging
from pathlib import Path

logger = logging.getLogger("c1b.metrics.bootstrap")

MULTIPROC_DIR = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "").strip()


def is_multiproc() -> bool:
    return bool(MULTIPROC_DIR)


def prepare_multiproc_dir() -> str:
    """Create + clear the multiproc dir at app boot. Called once from server lifespan."""
    if not is_multiproc():
        return ""
    p = Path(MULTIPROC_DIR)
    p.mkdir(parents=True, exist_ok=True)
    # remove .db files from previous boots — keeps gauges/histograms clean
    removed = 0
    for f in glob.glob(str(p / "*.db")):
        try:
            os.remove(f)
            removed += 1
        except OSError:
            pass
    logger.info("Prometheus multiproc dir prepared at %s (cleared %d stale files)", p, removed)
    return str(p)


def install_worker_death_hook():
    """Reap this process's metric files when it exits — required by prometheus_client."""
    if not is_multiproc():
        return
    try:
        from prometheus_client import multiprocess
    except Exception:
        return

    pid = os.getpid()

    def _cleanup(*_args):
        try:
            multiprocess.mark_process_dead(pid)
        except Exception:
            pass

    atexit.register(_cleanup)
    # also catch SIGTERM (kubernetes pod stop) and SIGINT (ctrl-c)
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            old = signal.getsignal(sig)
            def _handler(signum, frame, _old=old):
                _cleanup()
                if callable(_old) and _old not in (signal.SIG_DFL, signal.SIG_IGN):
                    _old(signum, frame)
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # signal.signal only works in main thread — uvicorn workers may not allow it
            pass
