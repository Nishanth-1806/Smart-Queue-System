"""
Comprehensive Data Seeder for Smart Queue Management System.
Seeds:
1. Default Administrator credentials (admin / admin123).
2. Multi-Sector Locations (Hospitals, Gov Offices, Transit, Banks, Malls, Theatres, Dining).
3. Hospital Departments & Doctors/Counters.
4. Active & Queued Hospital Patient Tokens.
5. CCTV Live Camera Streams with AI configs.
6. 30 Days of realistic hourly crowd & queue records.
"""

import sqlite3
import random
import datetime
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "smart_queue.db"


def hash_password(password: str) -> str:
    salt = "sq_salt_v2"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


LOCATIONS = [
    # ---------- 1. HOSPITALS & HEALTHCARE ----------
    {
        "name": "Apollo Multi-Speciality Hospital",
        "category": "Hospital",
        "cuisine": "Cardiology, General OPD, Pediatrics, Orthopedics, Radiology",
        "address": "2100 Webster Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7905,
        "lng": -122.4320,
        "rating": 4.9,
        "price_level": "$$$",
        "capacity": 220,
        "active_counters": 6,
        "avg_service_time_mins": 10,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=500&q=80",
        "phone": "+1 (415) 555-0800",
        "hours": "24 Hours / OPD: 08:00 AM - 08:00 PM",
        "description": "Premier multi-speciality tertiary care medical center with real-time digital token queue management for OPD consultations.",
        "departments": [
            {"name": "General Medicine OPD", "code": "GEN", "avg_service": 8, "doctors": 3, "limit": 60, "serving": 104},
            {"name": "Cardiology Clinic", "code": "CARD", "avg_service": 15, "doctors": 2, "limit": 40, "serving": 102},
            {"name": "Pediatric & Child Health", "code": "PED", "avg_service": 12, "doctors": 2, "limit": 50, "serving": 103},
            {"name": "Orthopedics & Joint Care", "code": "ORTH", "avg_service": 12, "doctors": 2, "limit": 45, "serving": 101},
            {"name": "Radiology & Diagnostic Scans", "code": "RAD", "avg_service": 10, "doctors": 3, "limit": 70, "serving": 106},
            {"name": "Emergency Triage", "code": "EMRG", "avg_service": 5, "doctors": 4, "limit": 100, "serving": 110},
        ],
        "pattern": "hospital"
    },
    {
        "name": "City General Memorial Hospital",
        "category": "Hospital",
        "cuisine": "Outpatient Triage, Internal Medicine, Neurology, Pharmacy",
        "address": "1001 Potrero Avenue",
        "area": "Mission",
        "city": "San Francisco",
        "lat": 37.7558,
        "lng": -122.4060,
        "rating": 4.7,
        "price_level": "$$",
        "capacity": 280,
        "active_counters": 8,
        "avg_service_time_mins": 9,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=500&q=80",
        "phone": "+1 (415) 555-0810",
        "hours": "24 Hours / Clinics: 08:30 AM - 06:30 PM",
        "description": "Major public general hospital offering affordable comprehensive healthcare and automated patient token queues.",
        "departments": [
            {"name": "Outpatient Triage (OPD)", "code": "OPD", "avg_service": 7, "doctors": 4, "limit": 80, "serving": 105},
            {"name": "Internal Medicine", "code": "MED", "avg_service": 10, "doctors": 3, "limit": 50, "serving": 102},
            {"name": "Neurology & Stroke Clinic", "code": "NEUR", "avg_service": 15, "doctors": 2, "limit": 30, "serving": 101},
            {"name": "Pharmacy & Dispensing Desk", "code": "PHARM", "avg_service": 4, "doctors": 5, "limit": 120, "serving": 115},
        ],
        "pattern": "hospital"
    },
    {
        "name": "Sunrise Children & Maternity Hospital",
        "category": "Hospital",
        "cuisine": "Pediatrics, Neonatal Care, Vaccination Clinic, Obstetrics",
        "address": "505 Parnassus Avenue",
        "area": "Midtown",
        "city": "San Francisco",
        "lat": 37.7635,
        "lng": -122.4580,
        "rating": 4.9,
        "price_level": "$$$",
        "capacity": 150,
        "active_counters": 4,
        "avg_service_time_mins": 12,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1538108149393-fbbd81895907?w=500&q=80",
        "phone": "+1 (415) 555-0822",
        "hours": "08:00 AM - 08:00 PM",
        "description": "Dedicated pediatric and maternity hospital featuring child-friendly queue systems and instant digital token passes.",
        "departments": [
            {"name": "Pediatric Outpatient Care", "code": "KIDS", "avg_service": 10, "doctors": 3, "limit": 60, "serving": 103},
            {"name": "Immunization & Vaccine Clinic", "code": "VAX", "avg_service": 6, "doctors": 2, "limit": 80, "serving": 108},
            {"name": "Maternity & Prenatal Care", "code": "MAT", "avg_service": 14, "doctors": 2, "limit": 40, "serving": 102},
        ],
        "pattern": "hospital"
    },

    # ---------- 2. GOVERNMENT & PUBLIC SERVICE OFFICES ----------
    {
        "name": "Regional Passport Seva Kendra",
        "category": "Government",
        "cuisine": "Passport Verification, Document Check, Biometrics",
        "address": "90 7th Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7788,
        "lng": -122.4110,
        "rating": 4.5,
        "price_level": "$",
        "capacity": 160,
        "active_counters": 6,
        "avg_service_time_mins": 8,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=500&q=80",
        "phone": "+1 (415) 555-0901",
        "hours": "09:00 AM - 05:00 PM (Mon-Fri)",
        "description": "Official regional passport processing and document verification centre with camera crowd analysis and token tracking.",
        "departments": [
            {"name": "Document Verification Counter A", "code": "DOC-A", "avg_service": 6, "doctors": 3, "limit": 90, "serving": 106},
            {"name": "Biometrics & Photo Capture", "code": "BIO", "avg_service": 5, "doctors": 4, "limit": 100, "serving": 109},
            {"name": "Senior Citizen & Tatkaal Desk", "code": "PRIO", "avg_service": 7, "doctors": 2, "limit": 40, "serving": 102},
        ],
        "pattern": "gov_office"
    },
    {
        "name": "District RTO & Vehicle Transport Office",
        "category": "Government",
        "cuisine": "Driving License, Vehicle Registration, Fitness Testing",
        "address": "1377 Fell Street",
        "area": "Midtown",
        "city": "San Francisco",
        "lat": 37.7735,
        "lng": -122.4390,
        "rating": 4.2,
        "price_level": "$",
        "capacity": 140,
        "active_counters": 5,
        "avg_service_time_mins": 7,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=500&q=80",
        "phone": "+1 (415) 555-0912",
        "hours": "08:30 AM - 04:30 PM (Mon-Fri)",
        "description": "District transport and motor vehicles registration center with live queue wait estimation.",
        "departments": [
            {"name": "Driving License Services", "code": "DL", "avg_service": 8, "doctors": 3, "limit": 75, "serving": 104},
            {"name": "Vehicle Registration & Transfer", "code": "RC", "avg_service": 6, "doctors": 2, "limit": 60, "serving": 103},
        ],
        "pattern": "gov_office"
    },
    {
        "name": "Municipal Citizen Service Kendra",
        "category": "Government",
        "cuisine": "Property Tax, Birth/Death Certificates, Civic Permits",
        "address": "1 Dr Carlton B Goodlett Place",
        "area": "Midtown",
        "city": "San Francisco",
        "lat": 37.7792,
        "lng": -122.4191,
        "rating": 4.6,
        "price_level": "$",
        "capacity": 120,
        "active_counters": 4,
        "avg_service_time_mins": 6,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1523292562811-8fa7962a78c8?w=500&q=80",
        "phone": "+1 (415) 555-0925",
        "hours": "09:00 AM - 05:00 PM",
        "description": "Unified municipal civic services office for municipal taxes, registrations, and public utility clearances.",
        "departments": [
            {"name": "Civic Certificates & Records", "code": "REC", "avg_service": 5, "doctors": 2, "limit": 80, "serving": 105},
            {"name": "Property Tax & Revenue", "code": "TAX", "avg_service": 7, "doctors": 2, "limit": 60, "serving": 102},
        ],
        "pattern": "gov_office"
    },

    # ---------- 3. RAILWAY & TRANSIT HUBS ----------
    {
        "name": "Grand Central Railway Junction",
        "category": "Transit",
        "cuisine": "Ticketing Counters, Reservation Lounge, Luggage Desk",
        "address": "4th & King Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7765,
        "lng": -122.3950,
        "rating": 4.6,
        "price_level": "$",
        "capacity": 450,
        "active_counters": 8,
        "avg_service_time_mins": 3,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=500&q=80",
        "phone": "+1 (415) 555-0701",
        "hours": "24 Hours Open",
        "description": "Major intercity passenger terminal with high-footfall ticketing concourses and AI crowd monitoring.",
        "pattern": "transit"
    },
    {
        "name": "Metro Central Bus Terminal",
        "category": "Transit",
        "cuisine": "Express Bus Ticketing, Concourse Queues, Information Desk",
        "address": "425 Mission Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7898,
        "lng": -122.3965,
        "rating": 4.5,
        "price_level": "$",
        "capacity": 250,
        "active_counters": 5,
        "avg_service_time_mins": 4,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=500&q=80",
        "phone": "+1 (415) 555-0715",
        "hours": "05:00 AM - 01:00 AM",
        "description": "Multi-tier metropolitan transit hub monitoring commuter queue density across boarding bays.",
        "pattern": "transit"
    },

    # ---------- 4. BANKS & FINANCIAL CENTERS ----------
    {
        "name": "State Central Commercial Bank",
        "category": "Bank",
        "cuisine": "Cash Deposit/Withdrawal, Foreign Exchange, Loan Advisory",
        "address": "300 Montgomery Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7918,
        "lng": -122.4025,
        "rating": 4.7,
        "price_level": "$$",
        "capacity": 90,
        "active_counters": 4,
        "avg_service_time_mins": 6,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1501167786227-4cba60f6d58f?w=500&q=80",
        "phone": "+1 (415) 555-0601",
        "hours": "09:30 AM - 04:30 PM (Mon-Sat)",
        "description": "Flagship financial center with teller queues, loan services, and smart customer token calling.",
        "departments": [
            {"name": "Cash & Teller Counters", "code": "CASH", "avg_service": 4, "doctors": 2, "limit": 100, "serving": 108},
            {"name": "Account & Customer Support", "code": "CS", "avg_service": 8, "doctors": 2, "limit": 50, "serving": 103},
        ],
        "pattern": "gov_office"
    },
    {
        "name": "City National Bank - Downtown Branch",
        "category": "Bank",
        "cuisine": "Personal Banking, Forex, NRI Services, Lockers",
        "address": "150 California Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7932,
        "lng": -122.3988,
        "rating": 4.6,
        "price_level": "$$",
        "capacity": 70,
        "active_counters": 3,
        "avg_service_time_mins": 5,
        "has_token_system": 1,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=500&q=80",
        "phone": "+1 (415) 555-0618",
        "hours": "09:30 AM - 04:00 PM (Mon-Fri)",
        "description": "Commercial branch equipped with digital token dispenser and live waiting time calculation.",
        "departments": [
            {"name": "Teller & Cash Services", "code": "TEL", "avg_service": 4, "doctors": 2, "limit": 70, "serving": 105},
        ],
        "pattern": "gov_office"
    },

    # ---------- 5. SHOPPING MALLS & SUPERMARKETS ----------
    {
        "name": "Grand Horizon Shopping Mall & Hypermarket",
        "category": "Shopping Mall",
        "cuisine": "Fashion Retail, Food Court, Hypermarket Checkout, Electronics",
        "address": "865 Market Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7845,
        "lng": -122.4065,
        "rating": 4.8,
        "price_level": "$$$",
        "capacity": 550,
        "active_counters": 12,
        "avg_service_time_mins": 3,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1519567241046-7f570eee3ce6?w=500&q=80",
        "phone": "+1 (415) 555-0501",
        "hours": "10:00 AM - 10:00 PM",
        "description": "Flagship multi-level retail destination monitoring customer rush across hypermarket checkouts and entrances.",
        "pattern": "mall"
    },
    {
        "name": "Westfield Retail & Entertainment Plaza",
        "category": "Shopping Mall",
        "cuisine": "Department Stores, Luxury Brands, Gourmet Food Court",
        "address": "845 Market Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7838,
        "lng": -122.4072,
        "rating": 4.7,
        "price_level": "$$$$",
        "capacity": 420,
        "active_counters": 10,
        "avg_service_time_mins": 3,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1567449303078-57ad995bd301?w=500&q=80",
        "phone": "+1 (415) 555-0512",
        "hours": "10:00 AM - 09:00 PM",
        "description": "Urban shopping destination with live occupancy monitoring and entry gate queue metrics.",
        "pattern": "mall"
    },

    # ---------- 6. THEATRES & ENTERTAINMENT ----------
    {
        "name": "PVR IMAX Multiplex & Cinema",
        "category": "Theatre",
        "cuisine": "IMAX 3D Movies, Gourmet Popcorn, Box Office Counters",
        "address": "135 4th Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7840,
        "lng": -122.4030,
        "rating": 4.8,
        "price_level": "$$$",
        "capacity": 320,
        "active_counters": 4,
        "avg_service_time_mins": 2,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80",
        "phone": "+1 (415) 555-0401",
        "hours": "11:00 AM - 11:30 PM",
        "description": "Premium multiplex theatre monitoring box office and concession stand queue times.",
        "pattern": "theatre"
    },
    {
        "name": "Grand Royal Opera & Concert Hall",
        "category": "Theatre",
        "cuisine": "Symphony, Ballet, Opera, VIP Lounge",
        "address": "301 Van Ness Avenue",
        "area": "Midtown",
        "city": "San Francisco",
        "lat": 37.7785,
        "lng": -122.4208,
        "rating": 4.9,
        "price_level": "$$$$",
        "capacity": 260,
        "active_counters": 3,
        "avg_service_time_mins": 3,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=500&q=80",
        "phone": "+1 (415) 555-0419",
        "hours": "05:00 PM - 11:00 PM (Show days)",
        "description": "Historic performing arts theatre with real-time auditorium entry queue management.",
        "pattern": "theatre"
    },

    # ---------- 7. RESTAURANTS & DINING ----------
    {
        "name": "Bella Italia Trattoria",
        "category": "Restaurant",
        "cuisine": "Woodfired Pizza, Handmade Pasta, Fine Wine",
        "address": "452 Market Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7891,
        "lng": -122.4014,
        "rating": 4.8,
        "price_level": "$$$",
        "capacity": 65,
        "active_counters": 2,
        "avg_service_time_mins": 35,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500&q=80",
        "phone": "+1 (415) 555-0142",
        "hours": "11:30 AM - 10:30 PM",
        "description": "Authentic Italian trattoria famous for wood-fired artisan pizza and handmade pasta.",
        "pattern": "dining"
    },
    {
        "name": "Sakura Artisanal Sushi & Omakase",
        "category": "Restaurant",
        "cuisine": "Sashimi, Nigiri, Matcha Cocktails",
        "address": "120 Pine Street",
        "area": "Downtown",
        "city": "San Francisco",
        "lat": 37.7915,
        "lng": -122.3980,
        "rating": 4.9,
        "price_level": "$$$$",
        "capacity": 36,
        "active_counters": 2,
        "avg_service_time_mins": 40,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=500&q=80",
        "phone": "+1 (415) 555-0199",
        "hours": "12:00 PM - 10:00 PM",
        "description": "High-end artisanal Japanese dining offering fresh omakase course menus.",
        "pattern": "dining"
    },
    {
        "name": "The Smokehouse Grill & Craft BBQ",
        "category": "Restaurant",
        "cuisine": "Texas Brisket, Smoked Ribs, Craft Beer",
        "address": "580 Valencia Street",
        "area": "Mission",
        "city": "San Francisco",
        "lat": 37.7630,
        "lng": -122.4218,
        "rating": 4.7,
        "price_level": "$$",
        "capacity": 85,
        "active_counters": 3,
        "avg_service_time_mins": 30,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=500&q=80",
        "phone": "+1 (415) 555-0177",
        "hours": "11:30 AM - 11:00 PM",
        "description": "Slow-smoked pit barbecue and craft brewery with high weekend footfall.",
        "pattern": "dining"
    },
    {
        "name": "Pier 39 Seafood & Oyster Bar",
        "category": "Restaurant",
        "cuisine": "Dungeness Crab, Clam Chowder, Fresh Oysters",
        "address": "The Embarcadero, Pier 39",
        "area": "Waterfront",
        "city": "San Francisco",
        "lat": 37.8086,
        "lng": -122.4098,
        "rating": 4.7,
        "price_level": "$$$",
        "capacity": 95,
        "active_counters": 3,
        "avg_service_time_mins": 35,
        "has_token_system": 0,
        "cctv_enabled": 1,
        "image_url": "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=500&q=80",
        "phone": "+1 (415) 555-0111",
        "hours": "11:00 AM - 10:00 PM",
        "description": "Scenic waterfront seafood restaurant specializing in freshly caught bay crab and oysters.",
        "pattern": "dining"
    }
]


def generate_hourly_count(capacity: int, hour: int, pattern: str, day_of_week: int) -> int:
    is_weekend = day_of_week in (5, 6)

    if pattern == "hospital":
        if 8 <= hour <= 13:
            occ = random.uniform(0.65, 0.92)
        elif 14 <= hour <= 19:
            occ = random.uniform(0.45, 0.75)
        elif 20 <= hour <= 23:
            occ = random.uniform(0.20, 0.38)
        else:
            occ = random.uniform(0.10, 0.22)
    elif pattern == "gov_office":
        if is_weekend:
            occ = 0.02
        elif 9 <= hour <= 12:
            occ = random.uniform(0.70, 0.95)
        elif 13 <= hour <= 16:
            occ = random.uniform(0.55, 0.85)
        else:
            occ = 0.05
    elif pattern == "transit":
        if hour in (8, 9, 17, 18, 19):
            occ = random.uniform(0.75, 0.96)
        elif 10 <= hour <= 16:
            occ = random.uniform(0.40, 0.65)
        else:
            occ = random.uniform(0.15, 0.35)
    elif pattern == "mall":
        if 11 <= hour <= 15:
            occ = random.uniform(0.50, 0.80) if not is_weekend else random.uniform(0.75, 0.96)
        elif 16 <= hour <= 21:
            occ = random.uniform(0.60, 0.88) if not is_weekend else random.uniform(0.85, 0.98)
        else:
            occ = random.uniform(0.05, 0.20)
    elif pattern == "theatre":
        if hour in (14, 15, 18, 19, 20, 21):
            occ = random.uniform(0.70, 0.95)
        else:
            occ = random.uniform(0.05, 0.25)
    else:  # dining
        if 12 <= hour <= 14:
            occ = random.uniform(0.60, 0.85)
        elif 19 <= hour <= 22:
            occ = random.uniform(0.75, 0.98)
        else:
            occ = random.uniform(0.05, 0.25)

    return max(0, min(capacity, round(capacity * occ)))


def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop existing tables to re-seed with clean comprehensive schema
    cur.execute("DROP TABLE IF EXISTS admin_users")
    cur.execute("DROP TABLE IF EXISTS tokens")
    cur.execute("DROP TABLE IF EXISTS departments")
    cur.execute("DROP TABLE IF EXISTS cctv_streams")
    cur.execute("DROP TABLE IF EXISTS crowd_logs")
    cur.execute("DROP TABLE IF EXISTS reports")
    cur.execute("DROP TABLE IF EXISTS locations")
    cur.execute("DROP TABLE IF EXISTS system_settings")

    # 1. Create Schema
    cur.execute("""
        CREATE TABLE admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE locations (
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

    cur.execute("""
        CREATE TABLE departments (
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

    cur.execute("""
        CREATE TABLE tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_number TEXT UNIQUE NOT NULL,
            location_id INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            patient_phone TEXT NOT NULL,
            slot_time TEXT DEFAULT 'Today',
            status TEXT NOT NULL DEFAULT 'WAITING',
            queue_position INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            estimated_call_time TEXT DEFAULT '',
            FOREIGN KEY (location_id) REFERENCES locations (id),
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    """)

    cur.execute("""
        CREATE TABLE cctv_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            stream_name TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'simulated',
            source_url TEXT DEFAULT '0',
            is_active INTEGER NOT NULL DEFAULT 1,
            fps INTEGER NOT NULL DEFAULT 15,
            last_detected_count INTEGER NOT NULL DEFAULT 0,
            last_status TEXT NOT NULL DEFAULT 'Online',
            last_updated TEXT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES locations (id)
        )
    """)

    cur.execute("""
        CREATE TABLE crowd_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            people_count INTEGER NOT NULL,
            queue_length INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'cv',
            FOREIGN KEY (location_id) REFERENCES locations (id)
        )
    """)

    cur.execute("""
        CREATE TABLE reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            wait_minutes INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES locations (id)
        )
    """)

    # 2. Seed Default Admin User (admin / admin123)
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")
    admin_pw = hash_password("admin123")
    cur.execute(
        "INSERT INTO admin_users (username, password_hash, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
        ("admin", admin_pw, "Super Administrator", "admin", now_iso)
    )
    print("[+] Seeded Admin Account: admin / admin123")

    # 3. Seed Locations & Departments
    location_id_map = {}
    dept_id_map = {}

    sample_patients = [
        ("Sarah Jenkins", "+1 415-555-0181"),
        ("David Zhao", "+1 415-555-0182"),
        ("Elena Rostova", "+1 415-555-0183"),
        ("Marcus Johnson", "+1 415-555-0184"),
        ("Priya Sharma", "+1 415-555-0185"),
        ("James Wilson", "+1 415-555-0186"),
        ("Chloe Martin", "+1 415-555-0187"),
        ("Ahmed Al-Mansoor", "+1 415-555-0188"),
    ]

    for loc in LOCATIONS:
        cur.execute(
            """
            INSERT INTO locations (
                name, category, cuisine, address, area, city, lat, lng, rating, price_level,
                capacity, active_counters, avg_service_time_mins, has_token_system, cctv_enabled,
                image_url, phone, hours, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loc["name"], loc["category"], loc["cuisine"], loc["address"], loc["area"], loc["city"],
                loc["lat"], loc["lng"], loc["rating"], loc["price_level"], loc["capacity"],
                loc["active_counters"], loc["avg_service_time_mins"], loc["has_token_system"],
                loc["cctv_enabled"], loc["image_url"], loc["phone"], loc["hours"], loc["description"]
            )
        )
        loc_id = cur.lastrowid
        location_id_map[loc["name"]] = loc_id

        # Seed CCTV Stream
        if loc["cctv_enabled"]:
            cur.execute(
                """
                INSERT INTO cctv_streams (location_id, stream_name, source_type, source_url, is_active, fps, last_status, last_updated)
                VALUES (?, ?, 'simulated', '0', 1, 15, 'Online', ?)
                """,
                (loc_id, f"CCTV - {loc['name']} Main Concourse", now_iso)
            )

        # Seed Departments & Sample Active Tokens
        if "departments" in loc:
            for dept in loc["departments"]:
                cur.execute(
                    """
                    INSERT INTO departments (location_id, name, code, avg_service_time_mins, active_doctors_or_counters, daily_token_limit, current_serving_token)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (loc_id, dept["name"], dept["code"], dept["avg_service"], dept["doctors"], dept["limit"], dept["serving"])
                )
                dept_id = cur.lastrowid
                dept_id_map[f"{loc_id}_{dept['code']}"] = dept_id

                # Seed sample active patient tokens in queue
                num_tokens = random.randint(3, 5)
                for i in range(num_tokens):
                    seq = dept["serving"] + i + 1
                    t_num = f"{dept['code']}-{seq}"
                    p_name, p_phone = sample_patients[(seq + dept_id) % len(sample_patients)]
                    wait_m = max(2, round((i * dept["avg_service"]) / max(1, dept["doctors"])))
                    c_time = (datetime.datetime.now() + datetime.timedelta(minutes=wait_m)).strftime("%I:%M %p")
                    cur.execute(
                        """
                        INSERT INTO tokens (token_number, location_id, department_id, patient_name, patient_phone, slot_time, status, queue_position, created_at, estimated_call_time)
                        VALUES (?, ?, ?, ?, ?, 'Today', 'WAITING', ?, ?, ?)
                        """,
                        (t_num, loc_id, dept_id, p_name, p_phone, i + 1, now_iso, c_time)
                    )

    print(f"[+] Seeded {len(LOCATIONS)} Public & Commercial Spaces with Departments & Tokens.")

    # 4. Seed 30 Days of Historical Crowd Logs
    start_date = datetime.datetime.now() - datetime.timedelta(days=30)
    total_logs = 0

    for loc in LOCATIONS:
        loc_id = location_id_map[loc["name"]]
        capacity = loc["capacity"]
        pattern = loc["pattern"]

        current_dt = start_date
        while current_dt <= datetime.datetime.now():
            hour = current_dt.hour
            dow = current_dt.weekday()
            count = generate_hourly_count(capacity, hour, pattern, dow)
            q_len = max(0, round(count * 0.6))
            ts = current_dt.isoformat(timespec="seconds")

            cur.execute(
                "INSERT INTO crowd_logs (location_id, timestamp, people_count, queue_length, source) VALUES (?, ?, ?, ?, 'cv')",
                (loc_id, ts, count, q_len)
            )
            total_logs += 1
            current_dt += datetime.timedelta(hours=1)

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Successfully seeded database with {total_logs} hourly crowd & queue records!")


if __name__ == "__main__":
    main()


