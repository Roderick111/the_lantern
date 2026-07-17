"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

# Set test DB path BEFORE any imports that may touch persistence
_worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
os.environ.setdefault("LANTERN_DB_PATH", f"saves/lantern_test_{_worker}.db")

# PLAYER_TOKEN for tests
os.environ.setdefault(
    "PLAYER_TOKEN_SECRET",
    "test-secret-for-pytest-minimum-thirty-two-characters-long",
)

# Add src to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(autouse=True)
def reset_llm_singleton():
    """Isolate LLM client between tests."""
    from src.api.llm_client import reset_llm_client

    reset_llm_client()
    yield
    reset_llm_client()


@pytest.fixture(autouse=True)
def clean_test_db():
    """Autouse: ensure test DB table exists and truncate saves between tests.

    Tests now hit real SQLite at LANTERN_DB_PATH.
    """
    from src.api.helpers import clear_state_cache
    from src.state.persistence import _get_conn, init_db

    init_db()
    clear_state_cache()
    yield
    clear_state_cache()
    conn = _get_conn()
    conn.execute("DELETE FROM saves")
    try:
        conn.execute("DELETE FROM idempotency_records")
    except Exception:
        pass
    conn.commit()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    """Session teardown: close conn and remove the test DB file."""
    yield
    try:
        from src.state.persistence import close_db

        close_db()
        db_path = os.environ.get("LANTERN_DB_PATH", "saves/lantern_test.db")
        p = Path(db_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def disable_rate_limiting() -> None:
    """Disable rate limiting during tests to prevent 429 errors."""
    from src.api.rate_limit import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def override_auth_dependency():
    """Bypass strict token auth in tests while preserving player_id routing.

    If a test sends a valid X-Player-Token header, the real token is verified.
    Otherwise falls back to extracting player_id from query params, request
    body, or "default". This keeps all existing tests passing while allowing
    auth-specific tests to exercise the real dependency.
    """
    from src.api.dependencies import get_authenticated_player_id
    from src.main import app

    async def _test_auth(request: Request) -> str:
        import re

        from fastapi import HTTPException

        token = request.headers.get("x-player-token")
        if token:
            from src.api.auth import verify_token

            pid = verify_token(token)
            if pid:
                request.state.player_id = pid
                return pid

        if "player_id" in request.query_params:
            pid = request.query_params["player_id"]
            if not re.match(r"^[a-zA-Z0-9_-]+$", pid):
                raise HTTPException(status_code=422, detail="Invalid player_id format")
            request.state.player_id = pid
            return pid

        try:
            body = await request.json()
            if isinstance(body, dict) and "player_id" in body:
                pid = body["player_id"]
                if not re.match(r"^[a-zA-Z0-9_-]+$", pid):
                    raise HTTPException(status_code=422, detail="Invalid player_id format")
                request.state.player_id = pid
                return pid
        except HTTPException:
            raise
        except Exception:
            pass

        request.state.player_id = "default"
        return "default"

    app.dependency_overrides[get_authenticated_player_id] = _test_auth
    yield
    app.dependency_overrides.pop(get_authenticated_player_id, None)
