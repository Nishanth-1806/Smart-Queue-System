"""
Loads real restaurant visitor data (Kaggle: Recruit Restaurant Visitor
Forecasting) into Smart Queue.

This dataset gives REAL daily visitor totals per restaurant -- it does
not publish hour-by-hour occupancy (no public dataset does, for
restaurants). To populate the hourly crowd_logs table our API expects,
each real daily total is distributed across hours using a realistic
lunch/dinner-peak shape.

Be upfront about this if asked: the *daily total* is real logged data;
the *hourly split* is a modeled estimate, not sensor ground truth. This
is a completely standard and defensible approach (the same technique
used to disaggregate any daily-only dataset), and it's a good thing to
be able to explain clearly in a viva.

Expected file: air_visit_data.csv with columns air_store_id, visit_date, visitors
Download from: https://www.kaggle.com/competitions/recruit-restaurant-visitor-forecasting/data
(free Kaggle account required)

Usage:
    python load_restaurant_data.py --csv data/air_visit_data.csv --restaurants 3
"""

import argparse
import csv
import datetime
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "smart_queue.db"

# Fraction of a day's visitors that arrive in each hour -- lunch peak
# around 12-13h, dinner peak around 19-20h, closed overnight.
HOURLY_SHAPE = [
    0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,   # 0-7
    0.01, 0.02, 0.04, 0.08, 0.14, 0.12, 0.06, 0.04,   # 8-15
    0.05, 0.07, 0.10, 0.14, 0.09, 0.03, 0.01, 0.00,   # 16-23
]
assert abs(sum(HOURLY_SHAPE) - 1.0) < 0.01


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            capacity INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crowd_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            people_count INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'cv',
            FOREIGN KEY (location_id) REFERENCES locations (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            wait_minutes INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (location_id) REFERENCES locations (id)
        )
    """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(Path(__file__).parent / "data" / "air_visit_data.csv"))
    parser.add_argument("--restaurants", type=int, default=3,
                         help="Number of distinct restaurants (by air_store_id) to import")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(
            f"Could not find {csv_path}.\n"
            f"Download air_visit_data.csv first -- see backend/data/README.md."
        )

    daily_by_store = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            store_id = row["air_store_id"]
            try:
                visit_date = datetime.datetime.strptime(row["visit_date"], "%Y-%m-%d").date()
                visitors = int(row["visitors"])
            except (ValueError, KeyError):
                continue
            daily_by_store[store_id].append((visit_date, visitors))

    chosen_stores = list(daily_by_store.keys())[: args.restaurants]
    if not chosen_stores:
        raise SystemExit("No rows found in the CSV -- check the file path/format.")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    if args.replace:
        conn.execute("DELETE FROM crowd_logs")
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM locations")

    total_rows = 0
    for i, store_id in enumerate(chosen_stores, start=1):
        daily_rows = daily_by_store[store_id]
        max_daily = max(v for _, v in daily_rows) or 1
        # Rough seating-capacity proxy: busiest single hour of the busiest day.
        capacity = max(1, round(max_daily * max(HOURLY_SHAPE)))

        cur = conn.execute(
            "INSERT INTO locations (name, category, capacity) VALUES (?, ?, ?)",
            (f"Restaurant {store_id[-6:]}", "restaurant", capacity),
        )
        location_id = cur.lastrowid

        rows_to_insert = []
        for visit_date, visitors in daily_rows:
            for hour, frac in enumerate(HOURLY_SHAPE):
                if frac == 0:
                    continue
                count = round(visitors * frac)
                ts = datetime.datetime.combine(visit_date, datetime.time(hour=hour))
                rows_to_insert.append((location_id, ts.isoformat(timespec="seconds"), count, "real_dataset_daily_disaggregated"))

        conn.executemany(
            "INSERT INTO crowd_logs (location_id, timestamp, people_count, source) VALUES (?, ?, ?, ?)",
            rows_to_insert,
        )
        total_rows += len(rows_to_insert)
        print(f"Loaded {store_id} as 'Restaurant {store_id[-6:]}': {len(daily_rows)} real daily totals "
              f"-> {len(rows_to_insert)} modeled hourly rows, capacity proxy={capacity}")

    conn.commit()
    conn.close()
    print(f"\nDone. {total_rows} crowd_logs rows across {len(chosen_stores)} restaurants.")
    print("Reminder: hourly split is modeled from real daily totals, not raw hourly ground truth.")


if __name__ == "__main__":
    main()
