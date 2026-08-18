#!/usr/bin/env bash
# Dependency audit — run from repo root. Uses project venv explicitly (not stray VIRTUAL_ENV).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Python (pip-audit) ==="
unset VIRTUAL_ENV
cd "$ROOT/backend"
uv sync --quiet
# pip is a tooling dep in the venv, not a runtime dep — keep it patched for audit.
uv pip install --quiet --upgrade 'pip>=26.1.2'
.venv/bin/python -m pip_audit

echo "=== Frontend (bun audit) ==="
cd "$ROOT/frontend"
~/.bun/bin/bun audit || true

echo "=== Done ==="