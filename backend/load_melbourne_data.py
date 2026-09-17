"""
Loads the City of Melbourne Pedestrian Counting System dataset (real
hourly footfall at named public/commercial locations) into the Smart
Queue database, replacing/augmenting the synthetic seed data.

Expected CSV columns (the dataset's native schema):
    Date_Time, Year, Month, Mdate, Day, Time, Sensor_ID, Sensor_Name, Hourly_Counts

See data/README.md for where to download this file from.

Usage:
    python load_melbourne_data.py --csv data/pedestrian_counts.csv \
        --sensors "Bourke Street Mall (North)" "Melbourne Central" \
        --days 60
"""

import argparse
import csv
import datetime
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "smart_queue.db"

DEFAULT_SENSORS = [
    "Bourke Street Mall (North)",
    "Melbourne Central",
    "Birrarung Marr",
]


def parse_datetime(date_time_str: str) -> datetime.datetime:
    """The dataset's Date_Time column is typically like '01-May-2019 08:00'."""
    for fmt in ("%d-%b-%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return datetime.datetime.strptime(date_time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised Date_Time format: {date_time_str}")


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
    parser.add_argument("--csv", default=str(Path(__file__).parent / "data" / "pedestrian_counts.csv"))
    parser.add_argument("--sensors", nargs="+", default=DEFAULT_SENSORS,
                         help="Sensor_Name values to import (see the dataset's Sensor Locations file for the full list)")
    parser.add_argument("--days", type=int, default=60,
                         help="Only import the most recent N days of data per sensor, to keep the demo DB small")
    parser.add_argument("--replace", action="store_true",
                         help="Wipe existing locations/crowd_logs before importing")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(
            f"Could not find {csv_path}.\n"
            f"Download the dataset first -- see backend/data/README.md for links."
        )

    # First pass: collect rows per requested sensor, keep only the most recent N days.
    rows_by_sensor = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_name = row.get("Sensor_Name")
            if sensor_name not in args.sensors:
                continue
            try:
                dt = parse_datetime(row["Date_Time"])
                count = int(float(row["Hourly_Counts"]))
            except (ValueError, KeyError):
                continue
            rows_by_sensor[sensor_name].append((dt, count))

    if not rows_by_sensor:
        raise SystemExit(
            "No matching rows found. Check that --sensors names match the "
            "Sensor_Name values exactly (see the dataset's Sensor Locations file)."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    if args.replace:
        conn.execute("DELETE FROM crowd_logs")
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM locations")

    total_inserted = 0
    for sensor_name, rows in rows_by_sensor.items():
        rows.sort(key=lambda r: r[0])
        if args.days:
            cutoff = rows[-1][0] - datetime.timedelta(days=args.days)
            rows = [r for r in rows if r[0] >= cutoff]

        counts = [c for _, c in rows]
        if not counts:
            continue
        # Capacity proxy: 95th-percentile observed count, so classification
        # thresholds (Low/Medium/High) are meaningful against this sensor's
        # own real range rather than an arbitrary fixed number.
        sorted_counts = sorted(counts)
        p95_index = min(len(sorted_counts) - 1, int(len(sorted_counts) * 0.95))
        capacity = max(sorted_counts[p95_index], 1)

        cur = conn.execute(
            "INSERT INTO locations (name, category, capacity) VALUES (?, ?, ?)",
            (f"{sensor_name} (Melbourne)", "public/commercial space", capacity),
        )
        location_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO crowd_logs (location_id, timestamp, people_count, source) VALUES (?, ?, ?, ?)",
            [(location_id, dt.isoformat(timespec="seconds"), count, "real_dataset") for dt, count in rows],
        )
        total_inserted += len(rows)
        print(f"Loaded {sensor_name!r}: {len(rows)} real hourly readings, capacity proxy={capacity}")

    conn.commit()
    conn.close()
    print(f"\nDone. Inserted {total_inserted} real crowd_logs rows across {len(rows_by_sensor)} locations.")


if __name__ == "__main__":
    main()
