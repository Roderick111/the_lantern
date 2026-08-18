"""FastAPI backend for HP Investigation Game.

Phase 1: Core Investigation Loop
- Freeform input -> LLM narrator -> Evidence discovery
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from src.api.rate_limit import limiter  # noqa: E402
from src.api.routes import router  # noqa: E402
from src.config.llm_settings import get_llm_settings  # noqa: E402
from src.state.persistence import close_db, init_db  # noqa: E402
from src.telemetry.logger import log_event  # noqa: E402

# Configure logging for debug output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — ensures DB connection cleanup on reload."""
    init_db()
    _llm = get_llm_settings()
    logger.info(
        "LLM config: model=%s, fallback=%s, provider=%s",
        _llm.DEFAULT_MODEL,
        _llm.FALLBACK_MODEL,
        _llm.DEFAULT_LLM_PROVIDER.value,
    )
    yield
    close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="HP Game Backend",
    description="Investigation game with Claude LLM narrator",
    version="0.4.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Max request body size: 8 KB (chat messages, verdicts, etc.)
MAX_BODY_SIZE = 8 * 1024


@app.middleware("http")
async def limit_request_body(request: Request, call_next) -> Response:
    """Reject requests with body larger than MAX_BODY_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
        )
    return await call_next(request)


# CORS — explicit origins from env (no wildcard with credentials). Validate.
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

# Tighten: disallow "*" when credentials=True (insecure + FastAPI rejects it)
if "*" in _cors_origins:
    logger.warning("CORS_ORIGINS contains '*'; stripping for security with credentials=True")
    _cors_origins = [o for o in _cors_origins if o != "*"]

if not _cors_origins:
    _cors_origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Startup/shutdown handled by lifespan context manager


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled exceptions to telemetry before returning 500."""
    await log_event(
        "server_error",
        "unknown",
        "unknown",
        {
            "path": str(request.url.path),
            "error": str(exc)[:200],
        },
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Include API routes
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    """Health check endpoint with DB connectivity verification."""
    from src.state.persistence import _get_conn

    db_ok = False
    try:
        conn = _get_conn()
        conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "HP Investigation Game API",
        "docs": "/docs",
        "health": "/health",
    }
