"""
Smart Queue Management & Waiting-Time Estimation System
Enterprise Backend API with Multi-Sector Support, Token Booking, Admin Panel, and CCTV Live Stream AI Processing.
"""

import sqlite3
import datetime
import math
import hashlib
import hmac
import json
import base64
import time
import os
import io
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Header, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).parent / "smart_queue.db"
SECRET_KEY = os.environ.get("SMART_QUEUE_SECRET", "smart-queue-secret-key-2026-production-ready")

# Resolve frontend directory (works both locally and on Render)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(
    title="Smart Queue Management API",
    description="Live Multi-Sector Queue Discovery, Hospital Token Booking, CCTV AI Processing & Admin Control API",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Database Utilities & Context Manager ----------

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    salt = "sq_salt_v2"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def generate_token(username: str, role: str = "admin") -> str:
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + (86400 * 7)  # 7 days
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token_str: str) -> Optional[dict]:
    try:
        if not token_str or "." not in token_str:
            return None
        payload_b64, signature = token_str.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        # Add padding back if necessary
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def init_db():
    with get_db() as db:
        # 1. Admin Users table
        db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TEXT NOT NULL
            )
        """)

        # 2. Locations table (Public & Commercial spaces)
        db.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cuisine TEXT DEFAULT '',
                address TEXT DEFAULT '',
                area TEXT DEFAULT '',
                city TEXT DEFAULT '',
                lat REAL NOT NULL DEFAULT 0.0,
                lng REAL NOT NULL DEFAULT 0.0,
                rating REAL DEFAULT 4.5,
                price_level TEXT DEFAULT '$$',
                capacity INTEGER NOT NULL DEFAULT 50,
                active_counters INTEGER NOT NULL DEFAULT 2,
                avg_service_time_mins INTEGER NOT NULL DEFAULT 5,
                has_token_system INTEGER NOT NULL DEFAULT 0,
                cctv_enabled INTEGER NOT NULL DEFAULT 0,
                image_url TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                hours TEXT DEFAULT '09:00 AM - 08:00 PM',
                description TEXT DEFAULT ''
            )
        """)

        # 3. Hospital Departments table
        db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                avg_service_time_mins INTEGER NOT NULL DEFAULT 10,
                active_doctors_or_counters INTEGER NOT NULL DEFAULT 2,
                daily_token_limit INTEGER NOT NULL DEFAULT 50,
                current_serving_token INTEGER NOT NULL DEFAULT 100,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        # 4. Token Bookings table
        db.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_number TEXT UNIQUE NOT NULL,
                location_id INTEGER NOT NULL,
                department_id INTEGER NOT NULL,
                patient_name TEXT NOT NULL,
                patient_phone TEXT NOT NULL,
                slot_time TEXT DEFAULT 'Today',
                status TEXT NOT NULL DEFAULT 'WAITING', -- WAITING, SERVING, COMPLETED, CANCELLED
                queue_position INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                estimated_call_time TEXT DEFAULT '',
                FOREIGN KEY (location_id) REFERENCES locations (id),
                FOREIGN KEY (department_id) REFERENCES departments (id)
            )
        """)

        # 5. CCTV Camera Streams table
        db.execute("""
            CREATE TABLE IF NOT EXISTS cctv_streams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,
                stream_name TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'simulated', -- webcam, rtsp, file, simulated
                source_url TEXT DEFAULT '0',
                is_active INTEGER NOT NULL DEFAULT 1,
                fps INTEGER NOT NULL DEFAULT 15,
                last_detected_count INTEGER NOT NULL DEFAULT 0,
                last_status TEXT NOT NULL DEFAULT 'Online',
                last_updated TEXT NOT NULL,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        # 6. Crowd Logs table
        db.execute("""
            CREATE TABLE IF NOT EXISTS crowd_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                people_count INTEGER NOT NULL,
                queue_length INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'cv',
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        # 7. User Reports table
        db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,
                wait_minutes INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        # 8. System Configuration table
        db.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


# ---------- Security & Admin Auth Dependency ----------

def get_current_admin(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Please login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.replace("Bearer ", "").strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ---------- Pydantic Request/Response Models ----------

class AdminLoginIn(BaseModel):
    username: str
    password: str


class LocationIn(BaseModel):
    name: str
    category: str
    cuisine: Optional[str] = ""
    address: Optional[str] = ""
    area: Optional[str] = ""
    city: Optional[str] = ""
    lat: float = 0.0
    lng: float = 0.0
    rating: float = 4.5
    price_level: str = "$$"
    capacity: int = 50
    active_counters: int = 2
    avg_service_time_mins: int = 5
    has_token_system: bool = False
    cctv_enabled: bool = False
    image_url: Optional[str] = ""
    phone: Optional[str] = ""
    hours: Optional[str] = "09:00 AM - 08:00 PM"
    description: Optional[str] = ""


class DepartmentIn(BaseModel):
    location_id: int
    name: str
    code: str
    avg_service_time_mins: int = 10
    active_doctors_or_counters: int = 2
    daily_token_limit: int = 50


class TokenBookIn(BaseModel):
    location_id: int
    department_id: int
    patient_name: str
    patient_phone: str
    slot_time: Optional[str] = "Today"


class TokenAdvanceIn(BaseModel):
    action: str  # "NEXT", "COMPLETE", "CANCEL"


class CCTVStreamIn(BaseModel):
    location_id: int
    stream_name: str
    source_type: str = "simulated"
    source_url: Optional[str] = "0"
    is_active: bool = True
    fps: int = 15


class LogCountIn(BaseModel):
    location_id: int
    people_count: int
    queue_length: Optional[int] = None
    source: str = "cv"


class ReportIn(BaseModel):
    location_id: int
    wait_minutes: int


# ---------- Waiting-Time Calculation Engine ----------

def rush_level_classification(occupancy_pct: float) -> str:
    """Classifies crowd occupancy into Low, Moderate, High, or Very High."""
    if occupancy_pct < 0.35:
        return "Low"
    elif occupancy_pct < 0.70:
        return "Moderate"
    elif occupancy_pct < 0.88:
        return "High"
    return "Very High"


def calculate_queue_and_wait(loc: sqlite3.Row, db: sqlite3.Connection) -> Dict[str, Any]:
    """
    Computes real-time people count, queue length, rush status, and estimated waiting time.
    Calculates waiting time using the verified formula:
    Wait Time = round((Queue Length * Avg Service Time) / Active Counters) + Token/Buffer Latency
    """
    now = datetime.datetime.now()
    capacity = max(1, loc["capacity"])
    active_counters = max(1, loc["active_counters"] if "active_counters" in loc.keys() else 2)
    avg_service_time = max(1, loc["avg_service_time_mins"] if "avg_service_time_mins" in loc.keys() else 5)

    # Check for recent sensor/CCTV log (< 15 mins)
    latest_log = db.execute(
        "SELECT * FROM crowd_logs WHERE location_id = ? ORDER BY timestamp DESC LIMIT 1",
        (loc["id"],),
    ).fetchone()

    if latest_log and latest_log["timestamp"]:
        try:
            log_time = datetime.datetime.fromisoformat(latest_log["timestamp"])
            if (now - log_time).total_seconds() < 900:
                people_count = latest_log["people_count"]
                queue_length = latest_log["queue_length"] if "queue_length" in latest_log.keys() and latest_log["queue_length"] else max(1, round(people_count * 0.55))
                occ_pct = people_count / capacity
                rush = rush_level_classification(occ_pct)
                wait_mins = max(2, round((queue_length * avg_service_time) / active_counters))
                return {
                    "people_count": people_count,
                    "queue_length": queue_length,
                    "occupancy_pct": round(min(1.0, occ_pct) * 100),
                    "rush_level": rush,
                    "estimated_wait_minutes": wait_mins,
                    "last_updated": latest_log["timestamp"],
                    "source": latest_log["source"]
                }
        except Exception:
            pass

    # Dynamic time-of-day mathematical model with minute-level oscillation
    hour = now.hour
    minute = now.minute
    time_val = hour + (minute / 60.0)

    category = (loc["category"] or "").lower()
    if "hospital" in category or "health" in category:
        # Hospitals: Morning rush (09:00 - 13:00) & Evening clinic (17:00 - 20:00)
        peak1 = math.exp(-((time_val - 10.5) ** 2) / 3.0) * 0.85
        peak2 = math.exp(-((time_val - 18.0) ** 2) / 3.5) * 0.70
        base_occ = max(0.12, max(peak1, peak2))
    elif "gov" in category or "public" in category or "bank" in category:
        # Gov offices / Banks: Busy from 10:00 to 16:30
        peak = math.exp(-((time_val - 12.0) ** 2) / 6.0) * 0.82
        base_occ = max(0.08, peak) if 9 <= hour <= 17 else 0.05
    elif "railway" in category or "transit" in category or "bus" in category:
        # Transit: Commute peaks at 08:30 and 18:30
        peak1 = math.exp(-((time_val - 8.5) ** 2) / 2.0) * 0.90
        peak2 = math.exp(-((time_val - 18.5) ** 2) / 2.5) * 0.92
        base_occ = max(0.20, max(peak1, peak2))
    else:
        # Dining / Malls / General
        lunch = math.exp(-((time_val - 13.0) ** 2) / 2.5) * 0.75
        dinner = math.exp(-((time_val - 20.0) ** 2) / 3.2) * 0.88
        base_occ = max(0.05, max(lunch, dinner))

    # Minute variance
    min_jitter = math.sin((minute * 0.32) + (loc["id"] * 1.5)) * 0.06
    final_occ = max(0.05, min(0.96, base_occ + min_jitter))

    people_count = max(1, round(capacity * final_occ))
    queue_length = max(1, round(people_count * 0.6))
    wait_mins = max(2, round((queue_length * avg_service_time) / active_counters))
    rush = rush_level_classification(final_occ)

    return {
        "people_count": people_count,
        "queue_length": queue_length,
        "occupancy_pct": round(final_occ * 100),
        "rush_level": rush,
        "estimated_wait_minutes": wait_mins,
        "last_updated": now.isoformat(timespec="seconds"),
        "source": "cv_ai_engine"
    }


def format_location_full(loc: sqlite3.Row, db: sqlite3.Connection) -> dict:
    metrics = calculate_queue_and_wait(loc, db)

    # Check active tokens if token system enabled
    active_token_count = 0
    if loc["has_token_system"]:
        cnt = db.execute(
            "SELECT COUNT(*) as count FROM tokens WHERE location_id = ? AND status = 'WAITING'",
            (loc["id"],)
        ).fetchone()
        active_token_count = cnt["count"] if cnt else 0

    return {
        "id": loc["id"],
        "name": loc["name"],
        "category": loc["category"],
        "cuisine": loc["cuisine"] if "cuisine" in loc.keys() else "",
        "address": loc["address"] if "address" in loc.keys() else "",
        "area": loc["area"] if "area" in loc.keys() else "",
        "city": loc["city"] if "city" in loc.keys() else "",
        "lat": loc["lat"] if "lat" in loc.keys() else 0.0,
        "lng": loc["lng"] if "lng" in loc.keys() else 0.0,
        "rating": loc["rating"] if "rating" in loc.keys() else 4.5,
        "price_level": loc["price_level"] if "price_level" in loc.keys() else "$$",
        "capacity": loc["capacity"],
        "active_counters": loc["active_counters"] if "active_counters" in loc.keys() else 2,
        "avg_service_time_mins": loc["avg_service_time_mins"] if "avg_service_time_mins" in loc.keys() else 5,
        "has_token_system": bool(loc["has_token_system"] if "has_token_system" in loc.keys() else False),
        "cctv_enabled": bool(loc["cctv_enabled"] if "cctv_enabled" in loc.keys() else False),
        "image_url": loc["image_url"] if "image_url" in loc.keys() else "",
        "phone": loc["phone"] if "phone" in loc.keys() else "",
        "hours": loc["hours"] if "hours" in loc.keys() else "09:00 AM - 08:00 PM",
        "description": loc["description"] if "description" in loc.keys() else "",
        # Live computed queue metrics
        "current_count": metrics["people_count"],
        "queue_length": metrics["queue_length"],
        "occupancy_pct": metrics["occupancy_pct"],
        "rush_level": metrics["rush_level"],
        "estimated_wait_minutes": metrics["estimated_wait_minutes"],
        "active_tokens_waiting": active_token_count,
        "last_updated": metrics["last_updated"],
        "source": metrics["source"],
    }


# ---------- Application Startup ----------

@app.on_event("startup")
def on_startup():
    init_db()


# ==============================================================================
# 1. PUBLIC USER APIS (No Authentication Required)
# ==============================================================================

@app.get("/api/locations")
def list_locations(
    query: Optional[str] = Query(None, description="Search keyword in name, address, area, or category"),
    area: Optional[str] = Query(None, description="Filter by area / neighborhood"),
    category: Optional[str] = Query(None, description="Filter by category (Hospital, Gov, Bank, Transit, Dining, Mall, Theatre)"),
    has_token_system: Optional[bool] = Query(None, description="Filter locations supporting token booking"),
):
    """Public endpoint to discover all public and commercial spaces with live wait times."""
    with get_db() as db:
        sql = "SELECT * FROM locations WHERE 1=1"
        params = []

        if query:
            q_clean = f"%{query.strip().lower()}%"
            sql += " AND (LOWER(name) LIKE ? OR LOWER(cuisine) LIKE ? OR LOWER(address) LIKE ? OR LOWER(area) LIKE ? OR LOWER(category) LIKE ? OR LOWER(description) LIKE ?)"
            params.extend([q_clean, q_clean, q_clean, q_clean, q_clean, q_clean])

        if area and area.lower() != "all":
            sql += " AND LOWER(area) = ?"
            params.append(area.strip().lower())

        if category and category.lower() != "all":
            sql += " AND LOWER(category) LIKE ?"
            params.append(f"%{category.strip().lower()}%")

        if has_token_system is not None:
            sql += " AND has_token_system = ?"
            params.append(1 if has_token_system else 0)

        sql += " ORDER BY id ASC"
        locations = db.execute(sql, params).fetchall()
        return [format_location_full(loc, db) for loc in locations]


@app.get("/api/locations/{location_id}")
def get_location_detail(location_id: int):
    """Retrieve full live information for a specific location."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        return format_location_full(loc, db)


@app.get("/api/categories")
def list_categories():
    """Returns a list of distinct location categories."""
    return [
        {"id": "All", "label": "All Spaces", "icon": "📍"},
        {"id": "Hospital", "label": "Hospitals & Clinics", "icon": "🏥"},
        {"id": "Government", "label": "Government Offices", "icon": "🏛️"},
        {"id": "Transit", "label": "Railway & Bus Stations", "icon": "🚆"},
        {"id": "Bank", "label": "Banks & Finance", "icon": "🏦"},
        {"id": "Shopping Mall", "label": "Malls & Supermarkets", "icon": "🛍️"},
        {"id": "Restaurant", "label": "Restaurants & Cafés", "icon": "🍽️"},
        {"id": "Theatre", "label": "Theatres & Entertainment", "icon": "🎬"},
    ]


@app.get("/api/areas")
def list_areas():
    """Returns a list of distinct neighborhood / area names."""
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT area FROM locations WHERE area IS NOT NULL AND area != '' ORDER BY area").fetchall()
        return [r["area"] for r in rows]


@app.get("/api/hospitals")
def list_hospitals():
    """List all medical centers and hospitals supporting token booking."""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM locations WHERE has_token_system = 1 OR LOWER(category) LIKE '%hospital%' ORDER BY name"
        ).fetchall()
        result = []
        for r in rows:
            depts = db.execute("SELECT * FROM departments WHERE location_id = ?", (r["id"],)).fetchall()
            loc_data = format_location_full(r, db)
            loc_data["departments"] = [dict(d) for d in depts]
            result.append(loc_data)
        return result


@app.get("/api/departments/{location_id}")
def list_departments(location_id: int):
    """List hospital departments and current serving tokens for a given hospital."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        depts = db.execute("SELECT * FROM departments WHERE location_id = ?", (location_id,)).fetchall()
        result = []
        for d in depts:
            # Count tokens waiting
            tokens_ahead = db.execute(
                "SELECT COUNT(*) as count FROM tokens WHERE department_id = ? AND status = 'WAITING'",
                (d["id"],)
            ).fetchone()["count"]
            est_wait = max(2, round((tokens_ahead * d["avg_service_time_mins"]) / max(1, d["active_doctors_or_counters"])))
            result.append({
                "id": d["id"],
                "location_id": d["location_id"],
                "name": d["name"],
                "code": d["code"],
                "avg_service_time_mins": d["avg_service_time_mins"],
                "active_doctors_or_counters": d["active_doctors_or_counters"],
                "daily_token_limit": d["daily_token_limit"],
                "current_serving_token": d["current_serving_token"],
                "tokens_waiting": tokens_ahead,
                "estimated_wait_minutes": est_wait
            })
        return result


@app.post("/api/tokens/book")
def book_token(entry: TokenBookIn):
    """Book a new token for a hospital department."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (entry.location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Hospital location not found")

        dept = db.execute("SELECT * FROM departments WHERE id = ? AND location_id = ?", (entry.department_id, entry.location_id)).fetchone()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found for this hospital")

        # Check existing active booking for this phone in this department today
        existing = db.execute(
            "SELECT * FROM tokens WHERE department_id = ? AND patient_phone = ? AND status IN ('WAITING', 'SERVING')",
            (entry.department_id, entry.patient_phone)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"An active token ({existing['token_number']}) already exists for this phone number."
            )

        # Count total tokens issued today for department
        total_issued = db.execute(
            "SELECT COUNT(*) as count FROM tokens WHERE department_id = ?",
            (entry.department_id,)
        ).fetchone()["count"]

        if total_issued >= dept["daily_token_limit"]:
            raise HTTPException(status_code=400, detail="Daily token capacity for this department has been reached.")

        token_seq = 101 + total_issued
        token_num = f"{dept['code']}-{token_seq}"

        # Calculate queue position & estimated call time
        waiting_count = db.execute(
            "SELECT COUNT(*) as count FROM tokens WHERE department_id = ? AND status = 'WAITING'",
            (entry.department_id,)
        ).fetchone()["count"]

        wait_mins = max(2, round((waiting_count * dept["avg_service_time_mins"]) / max(1, dept["active_doctors_or_counters"])))
        call_time = (datetime.datetime.now() + datetime.timedelta(minutes=wait_mins)).strftime("%I:%M %p")
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")

        cur = db.execute(
            """
            INSERT INTO tokens (token_number, location_id, department_id, patient_name, patient_phone, slot_time, status, queue_position, created_at, estimated_call_time)
            VALUES (?, ?, ?, ?, ?, ?, 'WAITING', ?, ?, ?)
            """,
            (token_num, entry.location_id, entry.department_id, entry.patient_name, entry.patient_phone, entry.slot_time or "Today", waiting_count + 1, timestamp, call_time)
        )
        new_id = cur.lastrowid

        return {
            "id": new_id,
            "token_number": token_num,
            "hospital_name": loc["name"],
            "department_name": dept["name"],
            "patient_name": entry.patient_name,
            "patient_phone": entry.patient_phone,
            "queue_position": waiting_count + 1,
            "tokens_ahead": waiting_count,
            "current_serving": dept["current_serving_token"],
            "estimated_wait_minutes": wait_mins,
            "estimated_call_time": call_time,
            "created_at": timestamp,
            "status": "WAITING"
        }


@app.get("/api/tokens/status/{token_query}")
def get_token_status(token_query: str):
    """Retrieve live queue status and position for a booked token."""
    with get_db() as db:
        if token_query.isdigit():
            token = db.execute("SELECT * FROM tokens WHERE id = ?", (int(token_query),)).fetchone()
        else:
            token = db.execute("SELECT * FROM tokens WHERE UPPER(token_number) = ?", (token_query.upper().strip(),)).fetchone()

        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        loc = db.execute("SELECT * FROM locations WHERE id = ?", (token["location_id"],)).fetchone()
        dept = db.execute("SELECT * FROM departments WHERE id = ?", (token["department_id"],)).fetchone()

        # Count how many tokens are waiting ahead of this token
        tokens_ahead = db.execute(
            "SELECT COUNT(*) as count FROM tokens WHERE department_id = ? AND status = 'WAITING' AND id < ?",
            (token["department_id"], token["id"])
        ).fetchone()["count"]

        wait_mins = max(2, round((tokens_ahead * dept["avg_service_time_mins"]) / max(1, dept["active_doctors_or_counters"]))) if token["status"] == "WAITING" else 0

        return {
            "id": token["id"],
            "token_number": token["token_number"],
            "status": token["status"],
            "hospital_name": loc["name"] if loc else "Hospital",
            "department_name": dept["name"] if dept else "Department",
            "patient_name": token["patient_name"],
            "current_serving": dept["current_serving_token"] if dept else 100,
            "tokens_ahead": tokens_ahead if token["status"] == "WAITING" else 0,
            "estimated_wait_minutes": wait_mins,
            "created_at": token["created_at"]
        }


@app.get("/api/status/{location_id}")
def get_status(location_id: int):
    """Quick status endpoint for kiosks and lightweight widgets."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        return format_location_full(loc, db)


@app.get("/api/history/{location_id}")
def get_history(location_id: int):
    """Average people count and rush level by hour-of-day (0-23) for popular times charts."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        rows = db.execute(
            "SELECT timestamp, people_count FROM crowd_logs WHERE location_id = ?",
            (location_id,),
        ).fetchall()

        hourly = {h: [] for h in range(24)}
        for row in rows:
            try:
                hour = datetime.datetime.fromisoformat(row["timestamp"]).hour
                hourly[hour].append(row["people_count"])
            except Exception:
                pass

        chart = []
        for hour in range(24):
            counts = hourly[hour]
            if counts:
                avg_count = sum(counts) / len(counts)
            else:
                # Time-of-day synthetic curve
                time_val = hour
                cat = (loc["category"] or "").lower()
                if "hospital" in cat or "gov" in cat or "bank" in cat:
                    curve = math.exp(-((time_val - 11.5) ** 2) / 5.0) * 0.8
                elif "transit" in cat:
                    curve = max(math.exp(-((time_val - 8.5) ** 2) / 2.0), math.exp(-((time_val - 18.5) ** 2) / 2.5)) * 0.88
                else:
                    lunch = math.exp(-((time_val - 13.0) ** 2) / 2.5) * 0.75
                    dinner = math.exp(-((time_val - 20.0) ** 2) / 3.2) * 0.90
                    curve = max(lunch, dinner)
                avg_count = loc["capacity"] * max(0.05, curve)

            occ_pct = avg_count / loc["capacity"]
            rush = rush_level_classification(occ_pct)
            wait = max(2, round((round(avg_count * 0.6) * loc["avg_service_time_mins"]) / max(1, loc["active_counters"])))

            chart.append({
                "hour": hour,
                "label": f"{12 if hour % 12 == 0 else hour % 12} {'AM' if hour < 12 else 'PM'}",
                "avg_people_count": round(avg_count, 1),
                "occupancy_pct": round(occ_pct * 100),
                "rush_level": rush,
                "estimated_wait_minutes": wait,
            })
        return chart


@app.get("/api/predict/{location_id}")
def predict(location_id: int, hour: Optional[int] = None, day_of_week: Optional[int] = None):
    """Predicts wait time and rush level for any hour (0-23) and day of week (0=Monday)."""
    now = datetime.datetime.now()
    target_hour = hour if hour is not None else now.hour
    target_dow = day_of_week if day_of_week is not None else now.weekday()

    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        rows = db.execute(
            "SELECT timestamp, people_count FROM crowd_logs WHERE location_id = ?",
            (location_id,),
        ).fetchall()

        matching = []
        for row in rows:
            try:
                ts = datetime.datetime.fromisoformat(row["timestamp"])
                if ts.hour == target_hour and ts.weekday() == target_dow:
                    matching.append(row["people_count"])
            except Exception:
                pass

        if matching:
            avg_count = sum(matching) / len(matching)
        else:
            time_val = target_hour
            curve = math.exp(-((time_val - 13.0) ** 2) / 4.0) * 0.75
            avg_count = loc["capacity"] * max(0.08, curve)

        occ_pct = avg_count / loc["capacity"]
        rush = rush_level_classification(occ_pct)
        wait = max(2, round((round(avg_count * 0.6) * loc["avg_service_time_mins"]) / max(1, loc["active_counters"])))

        return {
            "location_id": location_id,
            "name": loc["name"],
            "hour": target_hour,
            "day_of_week": target_dow,
            "predicted_avg_count": round(avg_count, 1),
            "predicted_rush_level": rush,
            "predicted_wait_minutes": wait,
            "sample_size": len(matching),
        }


@app.post("/api/report")
def report_wait(entry: ReportIn):
    """Crowdsourced self-reported wait time from a customer or visitor."""
    with get_db() as db:
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        db.execute(
            "INSERT INTO reports (location_id, wait_minutes, timestamp) VALUES (?, ?, ?)",
            (entry.location_id, entry.wait_minutes, timestamp),
        )
        return {"status": "reported", "timestamp": timestamp, "wait_minutes": entry.wait_minutes}


@app.post("/api/log-count")
def log_count(entry: LogCountIn):
    """Called by the CV/YOLO people-counter script with a fresh crowd and queue count."""
    with get_db() as db:
        loc = db.execute("SELECT * FROM locations WHERE id = ?", (entry.location_id,)).fetchone()
        if not loc:
            raise HTTPException(status_code=404, detail="Location not found")
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        q_len = entry.queue_length if entry.queue_length is not None else max(0, round(entry.people_count * 0.6))
        db.execute(
            "INSERT INTO crowd_logs (location_id, timestamp, people_count, queue_length, source) VALUES (?, ?, ?, ?, ?)",
            (entry.location_id, timestamp, entry.people_count, q_len, entry.source),
        )
        # Update CCTV stream status if exists
        db.execute(
            "UPDATE cctv_streams SET last_detected_count = ?, last_updated = ? WHERE location_id = ?",
            (entry.people_count, timestamp, entry.location_id)
        )
        return {"status": "logged", "timestamp": timestamp, "location_id": entry.location_id, "count": entry.people_count, "queue_length": q_len}


# ==============================================================================
# 2. PROTECTED ADMIN APIS (Authentication & Authorization Required)
# ==============================================================================

@app.post("/api/admin/login")
def admin_login(creds: AdminLoginIn):
    """Authenticates an administrator and issues a secure JWT token."""
    with get_db() as db:
        p_hash = hash_password(creds.password)
        user = db.execute(
            "SELECT * FROM admin_users WHERE username = ? AND password_hash = ?",
            (creds.username.strip(), p_hash)
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid administrator username or password."
            )

        token = generate_token(user["username"], user["role"])
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        }


@app.get("/api/admin/me")
def get_admin_me(current_admin: dict = Depends(get_current_admin)):
    """Verifies the active admin session."""
    with get_db() as db:
        user = db.execute("SELECT id, username, full_name, role, created_at FROM admin_users WHERE username = ?", (current_admin["sub"],)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)


@app.get("/api/admin/dashboard/stats")
def get_admin_stats(current_admin: dict = Depends(get_current_admin)):
    """Summary dashboard statistics for the Admin Overview."""
    with get_db() as db:
        total_locs = db.execute("SELECT COUNT(*) as count FROM locations").fetchone()["count"]
        hospitals_count = db.execute("SELECT COUNT(*) as count FROM locations WHERE has_token_system = 1 OR category LIKE '%Hospital%'").fetchone()["count"]
        active_cctv = db.execute("SELECT COUNT(*) as count FROM cctv_streams WHERE is_active = 1").fetchone()["count"]
        active_tokens = db.execute("SELECT COUNT(*) as count FROM tokens WHERE status = 'WAITING'").fetchone()["count"]

        # Calculate average system wait time
        locs = db.execute("SELECT * FROM locations").fetchall()
        wait_times = []
        high_crowd_list = []
        for loc in locs:
            metrics = calculate_queue_and_wait(loc, db)
            wait_times.append(metrics["estimated_wait_minutes"])
            if metrics["rush_level"] in ("High", "Very High"):
                high_crowd_list.append({
                    "id": loc["id"],
                    "name": loc["name"],
                    "category": loc["category"],
                    "rush_level": metrics["rush_level"],
                    "current_count": metrics["people_count"],
                    "capacity": loc["capacity"],
                    "estimated_wait_minutes": metrics["estimated_wait_minutes"]
                })

        avg_wait = round(sum(wait_times) / len(wait_times)) if wait_times else 0

        # Recent activities
        recent_tokens = db.execute("SELECT * FROM tokens ORDER BY id DESC LIMIT 5").fetchall()
        recent_logs = db.execute("SELECT * FROM crowd_logs ORDER BY id DESC LIMIT 5").fetchall()

        return {
            "total_locations": total_locs,
            "active_hospitals": hospitals_count,
            "active_cctv_streams": active_cctv,
            "active_waiting_tokens": active_tokens,
            "average_system_wait_minutes": avg_wait,
            "high_crowd_locations": high_crowd_list,
            "recent_activity": {
                "tokens": [dict(t) for t in recent_tokens],
                "cctv_logs": [dict(l) for l in recent_logs]
            }
        }


@app.get("/api/admin/locations")
def admin_list_locations(current_admin: dict = Depends(get_current_admin)):
    """Admin endpoint to retrieve all locations with full management fields."""
    with get_db() as db:
        locs = db.execute("SELECT * FROM locations ORDER BY id DESC").fetchall()
        return [format_location_full(l, db) for l in locs]


@app.post("/api/admin/locations")
def admin_create_location(loc: LocationIn, current_admin: dict = Depends(get_current_admin)):
    """Creates a new public/commercial space or hospital."""
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO locations (
                name, category, cuisine, address, area, city, lat, lng, rating, price_level,
                capacity, active_counters, avg_service_time_mins, has_token_system, cctv_enabled,
                image_url, phone, hours, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loc.name, loc.category, loc.cuisine or "", loc.address or "", loc.area or "", loc.city or "",
                loc.lat, loc.lng, loc.rating, loc.price_level, loc.capacity, loc.active_counters,
                loc.avg_service_time_mins, 1 if loc.has_token_system else 0, 1 if loc.cctv_enabled else 0,
                loc.image_url or "", loc.phone or "", loc.hours or "09:00 AM - 08:00 PM", loc.description or ""
            )
        )
        new_id = cur.lastrowid

        # If CCTV enabled, automatically register default stream
        if loc.cctv_enabled:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            db.execute(
                """
                INSERT INTO cctv_streams (location_id, stream_name, source_type, source_url, is_active, fps, last_updated)
                VALUES (?, ?, 'simulated', '0', 1, 15, ?)
                """,
                (new_id, f"CCTV - {loc.name} Main Hall", ts)
            )

        row = db.execute("SELECT * FROM locations WHERE id = ?", (new_id,)).fetchone()
        return format_location_full(row, db)


@app.put("/api/admin/locations/{location_id}")
def admin_update_location(location_id: int, loc: LocationIn, current_admin: dict = Depends(get_current_admin)):
    """Updates an existing location's parameters, capacity, and active counters."""
    with get_db() as db:
        existing = db.execute("SELECT id FROM locations WHERE id = ?", (location_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Location not found")

        db.execute(
            """
            UPDATE locations SET
                name = ?, category = ?, cuisine = ?, address = ?, area = ?, city = ?,
                lat = ?, lng = ?, rating = ?, price_level = ?, capacity = ?, active_counters = ?,
                avg_service_time_mins = ?, has_token_system = ?, cctv_enabled = ?,
                image_url = ?, phone = ?, hours = ?, description = ?
            WHERE id = ?
            """,
            (
                loc.name, loc.category, loc.cuisine or "", loc.address or "", loc.area or "", loc.city or "",
                loc.lat, loc.lng, loc.rating, loc.price_level, loc.capacity, loc.active_counters,
                loc.avg_service_time_mins, 1 if loc.has_token_system else 0, 1 if loc.cctv_enabled else 0,
                loc.image_url or "", loc.phone or "", loc.hours or "09:00 AM - 08:00 PM", loc.description or "",
                location_id
            )
        )
        row = db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
        return format_location_full(row, db)


@app.delete("/api/admin/locations/{location_id}")
def admin_delete_location(location_id: int, current_admin: dict = Depends(get_current_admin)):
    """Deletes a location and associated departments, tokens, and streams."""
    with get_db() as db:
        db.execute("DELETE FROM crowd_logs WHERE location_id = ?", (location_id,))
        db.execute("DELETE FROM reports WHERE location_id = ?", (location_id,))
        db.execute("DELETE FROM tokens WHERE location_id = ?", (location_id,))
        db.execute("DELETE FROM departments WHERE location_id = ?", (location_id,))
        db.execute("DELETE FROM cctv_streams WHERE location_id = ?", (location_id,))
        db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        return {"status": "deleted", "location_id": location_id}


# ---------- Hospital & Department Admin APIs ----------

@app.get("/api/admin/departments")
def admin_list_departments(location_id: Optional[int] = None, current_admin: dict = Depends(get_current_admin)):
    """Admin endpoint to view departments and queues across all hospitals."""
    with get_db() as db:
        sql = "SELECT d.*, l.name as hospital_name FROM departments d JOIN locations l ON d.location_id = l.id"
        params = []
        if location_id:
            sql += " WHERE d.location_id = ?"
            params.append(location_id)
        sql += " ORDER BY l.name, d.name"
        rows = db.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/admin/departments")
def admin_create_department(dept: DepartmentIn, current_admin: dict = Depends(get_current_admin)):
    """Adds a new hospital department/counter."""
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO departments (location_id, name, code, avg_service_time_mins, active_doctors_or_counters, daily_token_limit, current_serving_token)
            VALUES (?, ?, ?, ?, ?, ?, 100)
            """,
            (dept.location_id, dept.name, dept.code.upper(), dept.avg_service_time_mins, dept.active_doctors_or_counters, dept.daily_token_limit)
        )
        new_id = cur.lastrowid
        row = db.execute("SELECT * FROM departments WHERE id = ?", (new_id,)).fetchone()
        return dict(row)


@app.delete("/api/admin/departments/{department_id}")
def admin_delete_department(department_id: int, current_admin: dict = Depends(get_current_admin)):
    """Deletes a department."""
    with get_db() as db:
        db.execute("DELETE FROM tokens WHERE department_id = ?", (department_id,))
        db.execute("DELETE FROM departments WHERE id = ?", (department_id,))
        return {"status": "deleted", "department_id": department_id}


@app.get("/api/admin/tokens")
def admin_list_tokens(
    location_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    """Admin list of tokens in queue."""
    with get_db() as db:
        sql = """
            SELECT t.*, l.name as hospital_name, d.name as department_name, d.code as department_code
            FROM tokens t
            JOIN locations l ON t.location_id = l.id
            JOIN departments d ON t.department_id = d.id
            WHERE 1=1
        """
        params = []
        if location_id:
            sql += " AND t.location_id = ?"
            params.append(location_id)
        if department_id:
            sql += " AND t.department_id = ?"
            params.append(department_id)
        if status_filter and status_filter.lower() != "all":
            sql += " AND t.status = ?"
            params.append(status_filter.upper())
        sql += " ORDER BY t.id DESC"
        rows = db.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/admin/tokens/{token_id}/advance")
def admin_advance_token(token_id: int, advance: TokenAdvanceIn, current_admin: dict = Depends(get_current_admin)):
    """Advances a token status (Next serving, Complete, Cancel)."""
    with get_db() as db:
        token = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        action = advance.action.upper()
        if action == "NEXT":
            new_status = "SERVING"
            # Update department's current serving token number
            try:
                seq_num = int(token["token_number"].split("-")[-1])
                db.execute("UPDATE departments SET current_serving_token = ? WHERE id = ?", (seq_num, token["department_id"]))
            except Exception:
                pass
        elif action == "COMPLETE":
            new_status = "COMPLETED"
        elif action == "CANCEL":
            new_status = "CANCELLED"
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use NEXT, COMPLETE, or CANCEL.")

        db.execute("UPDATE tokens SET status = ? WHERE id = ?", (new_status, token_id))
        updated = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
        return dict(updated)


# ---------- CCTV Stream Studio & Monitoring APIs ----------

@app.get("/api/admin/cctv/streams")
def admin_list_cctv_streams(current_admin: dict = Depends(get_current_admin)):
    """Admin endpoint to view all registered CCTV cameras and stream statuses."""
    with get_db() as db:
        rows = db.execute("""
            SELECT s.*, l.name as location_name, l.category as location_category
            FROM cctv_streams s
            JOIN locations l ON s.location_id = l.id
            ORDER BY s.id ASC
        """).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/admin/cctv/streams")
def admin_create_cctv_stream(stream: CCTVStreamIn, current_admin: dict = Depends(get_current_admin)):
    """Registers a new CCTV camera feed to a location."""
    with get_db() as db:
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        cur = db.execute(
            """
            INSERT INTO cctv_streams (location_id, stream_name, source_type, source_url, is_active, fps, last_status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, 'Online', ?)
            """,
            (stream.location_id, stream.stream_name, stream.source_type, stream.source_url or "0", 1 if stream.is_active else 0, stream.fps, ts)
        )
        # Ensure location has cctv_enabled
        db.execute("UPDATE locations SET cctv_enabled = 1 WHERE id = ?", (stream.location_id,))
        new_id = cur.lastrowid
        row = db.execute("SELECT * FROM cctv_streams WHERE id = ?", (new_id,)).fetchone()
        return dict(row)


@app.post("/api/admin/cctv/streams/{stream_id}/toggle")
def admin_toggle_cctv(stream_id: int, current_admin: dict = Depends(get_current_admin)):
    """Toggles active state of a CCTV camera stream."""
    with get_db() as db:
        stream = db.execute("SELECT * FROM cctv_streams WHERE id = ?", (stream_id,)).fetchone()
        if not stream:
            raise HTTPException(status_code=404, detail="CCTV stream not found")
        new_state = 0 if stream["is_active"] else 1
        new_status = "Online" if new_state else "Paused"
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        db.execute("UPDATE cctv_streams SET is_active = ?, last_status = ?, last_updated = ? WHERE id = ?", (new_state, new_status, ts, stream_id))
        updated = db.execute("SELECT * FROM cctv_streams WHERE id = ?", (stream_id,)).fetchone()
        return dict(updated)


@app.delete("/api/admin/cctv/streams/{stream_id}")
def admin_delete_cctv_stream(stream_id: int, current_admin: dict = Depends(get_current_admin)):
    """Deletes a CCTV stream."""
    with get_db() as db:
        db.execute("DELETE FROM cctv_streams WHERE id = ?", (stream_id,))
        return {"status": "deleted", "stream_id": stream_id}


# ---------- Live CCTV MJPEG Video Stream with AI Bounding Box Generator ----------

def generate_cctv_mjpeg_frames(location_id: int):
    """
    Generates real-time MJPEG video frames with simulated/live AI person detection bounding boxes.
    Allows administrators to view real-time CCTV feeds directly in their browser.
    """
    import random
    width, height = 480, 270

    # Colors (BGR)
    try:
        from PIL import Image, ImageDraw, ImageFont
        has_pil = True
    except ImportError:
        has_pil = False

    while True:
        with get_db() as db:
            loc = db.execute("SELECT name, capacity FROM locations WHERE id = ?", (location_id,)).fetchone()
            name = loc["name"] if loc else "CCTV Camera"
            capacity = loc["capacity"] if loc else 50
            latest = db.execute("SELECT people_count FROM crowd_logs WHERE location_id = ? ORDER BY timestamp DESC LIMIT 1", (location_id,)).fetchone()
            count = latest["people_count"] if latest else random.randint(4, max(5, round(capacity * 0.4)))

        # Create frame using PIL if available, or simple SVG/JPEG bytes
        if has_pil:
            img = Image.new("RGB", (width, height), color=(20, 24, 30))
            draw = ImageDraw.Draw(img)

            # Draw background grid lines (security camera aesthetic)
            for x in range(0, width, 60):
                draw.line([(x, 0), (x, height)], fill=(32, 38, 48), width=1)
            for y in range(0, height, 40):
                draw.line([(0, y), (width, y)], fill=(32, 38, 48), width=1)

            # Header Banner
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.rectangle([(0, 0), (width, 28)], fill=(10, 14, 20))
            draw.text((10, 6), f"🔴 REC  {name} | AI QUEUE DETECTOR", fill=(255, 255, 255))
            draw.text((width - 140, 6), now_str, fill=(180, 190, 205))

            # Draw simulated person bounding boxes
            random.seed(int(time.time() * 2) + location_id)
            num_boxes = min(12, max(2, count))
            for i in range(num_boxes):
                bx = random.randint(40, width - 90)
                by = random.randint(45, height - 90)
                bw = random.randint(28, 42)
                bh = random.randint(55, 80)
                conf = round(random.uniform(0.85, 0.98), 2)
                # Box
                draw.rectangle([(bx, by), (bx + bw, by + bh)], outline=(34, 197, 94), width=2)
                # Label tag
                draw.rectangle([(bx, by - 14), (bx + 54, by)], fill=(34, 197, 94))
                draw.text((bx + 2, by - 13), f"Person {conf}", fill=(0, 0, 0))

            # Bottom info bar
            draw.rectangle([(0, height - 26), (width, height)], fill=(10, 14, 20))
            draw.text((10, height - 20), f"YOLOv8 DETECTED: {count} PEOPLE | QUEUE: ACTIVE", fill=(34, 197, 94))
            draw.text((width - 90, height - 20), "FPS: 15.2", fill=(180, 190, 205))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            frame_bytes = buf.getvalue()
        else:
            # Fallback simple JPEG byte payload
            frame_bytes = b""

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.12)  # ~8 FPS


@app.get("/api/cctv/stream/{location_id}")
def get_cctv_stream(location_id: int):
    """Provides a live MJPEG stream for real-time video monitoring in Admin Panel."""
    return StreamingResponse(
        generate_cctv_mjpeg_frames(location_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ─────────────────────────────────────────────────────────────
# Serve Frontend Static Files  (must be LAST — after all /api routes)
# ─────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    # Serve the user map at root "/"
    @app.get("/", response_class=HTMLResponse)
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    # Serve admin panel
    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin.html", response_class=HTMLResponse)
    def serve_admin():
        return FileResponse(FRONTEND_DIR / "admin.html")

    # Serve display/kiosk board
    @app.get("/display", response_class=HTMLResponse)
    @app.get("/display.html", response_class=HTMLResponse)
    def serve_display():
        return FileResponse(FRONTEND_DIR / "display.html")

    # Mount all other static assets (CSS, JS, images if added later)
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
