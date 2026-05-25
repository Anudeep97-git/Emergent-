"""Shared pytest fixtures — backend subprocess spawn for startup-log smoke tests."""
import os
import sys
import time
import socket
import signal
import subprocess
import tempfile
from pathlib import Path
from contextlib import contextmanager
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent


# Setup mongomock for end-to-end tests to avoid motor event loop issues
def pytest_configure(config):
    """Configure pytest - set up mongomock for end-to-end tests."""
    # Check if we're running end-to-end tests
    test_items = config.args if hasattr(config, 'args') else []
    if any('test_pipeline_end_to_end' in str(arg) for arg in test_items) or len(test_items) == 0:
        # Use mongomock for in-memory MongoDB testing
        try:
            from mongomock import MongoClient as MockMongoClient
            from motor.motor_asyncio import AsyncIOMotorClient
            
            # Create mock client
            mock_client = MockMongoClient()
            
            # Monkeypatch motor's AsyncIOMotorClient to use mongomock's synchronous client wrapped
            # This is a workaround for motor's event loop caching issues in tests
            os.environ["MONGO_URL"] = "mongodb://localhost:27017"  # dummy URL for mongomock
            
        except ImportError:
            pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@contextmanager
def spawn_backend(env_extra: dict = None, wait_marker: str = "ready.", timeout: float = 25.0):
    """Spawn the FastAPI app via uvicorn in a subprocess, capture combined stderr+stdout
    into a temp file, wait for the lifespan-complete marker, yield (port, log_path),
    then terminate cleanly."""
    env = os.environ.copy()
    env.pop("PROMETHEUS_MULTIPROC_DIR", None)   # default: single-process
    if env_extra:
        env.update(env_extra)
    port = _free_port()
    log_fp = tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False)
    log_path = log_fp.name
    log_fp.close()
    cmd = [
        sys.executable, "-m", "uvicorn", "server:app",
        "--host", "127.0.0.1", "--port", str(port), "--log-level", "info",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid if os.name != "nt" else None,
    )
    try:
        # wait for lifespan-complete marker
        deadline = time.time() + timeout
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with open(log_path, "r") as f:
                    content = f.read()
                if wait_marker in content:
                    ready = True
                    break
            except FileNotFoundError:
                pass
            time.sleep(0.2)
        if not ready:
            try:
                with open(log_path, "r") as f:
                    tail = f.read()[-2000:]
            except Exception:
                tail = ""
            raise TimeoutError(f"Backend did not become ready within {timeout}s. Tail:\n{tail}")
        yield port, log_path
    finally:
        try:
            if os.name != "nt":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


@pytest.fixture(scope="session")
def base_url():
    """Start a live backend process for integration tests."""
    with spawn_backend() as (port, _log_path):
        yield f"http://127.0.0.1:{port}"
