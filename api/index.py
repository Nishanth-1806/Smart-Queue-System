"""
Vercel Serverless Entry Point for Smart Queue Management System.
This file imports the FastAPI app and patches the DB path to use /tmp
(Vercel's writable directory) so SQLite works in the serverless environment.
"""

import sys
import os
from pathlib import Path

# ── Point to writable /tmp on Vercel, local path otherwise ──────────────────
IS_VERCEL = os.environ.get("VERCEL", "") == "1"

if IS_VERCEL:
    # Vercel: only /tmp is writable
    os.environ["SMART_QUEUE_DB_PATH"] = "/tmp/smart_queue.db"
else:
    # Local fallback
    db_local = Path(__file__).parent.parent / "backend" / "smart_queue.db"
    os.environ["SMART_QUEUE_DB_PATH"] = str(db_local)

# ── Add backend to Python path ───────────────────────────────────────────────
backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# ── Import the FastAPI app ───────────────────────────────────────────────────
from main import app  # noqa: E402

# Vercel expects the app to be named `app`
__all__ = ["app"]
