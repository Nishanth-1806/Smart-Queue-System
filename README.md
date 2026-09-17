# Smart Queue

Real-time crowd density and wait-time prediction system for public service
centers and businesses.

## Project structure

```
smart-queue/
├── backend/
│   ├── main.py           FastAPI app: all API endpoints
│   ├── seed_data.py       Generates 30 days of synthetic demo data
│   ├── cv_logger.py       YOLOv8 webcam people-counter (optional, run separately)
│   ├── requirements.txt
│   └── smart_queue.db     SQLite database (created automatically)
└── frontend/
    ├── index.html         Public dashboard — list of locations + charts
    └── display.html       Kiosk display board — for a monitor outside a location
```

## 1. Run the backend

```bash
cd backend
pip install -r requirements.txt

# Option A: synthetic demo data (works instantly, no download needed)
python seed_data.py

# Option B: real-world data (see data/README.md to download the dataset first)
python load_melbourne_data.py --days 60 --replace     # real public/commercial footfall
python load_restaurant_data.py --restaurants 3         # real restaurant visitor data

# Start the API server
uvicorn main:app --reload --port 8000
```

**About the real dataset:** `load_melbourne_data.py` loads the City of
Melbourne Pedestrian Counting System — genuine hourly footfall counts
since 2009 from real named public/commercial locations (retail malls,
transit precincts, public squares). `load_restaurant_data.py` loads
real daily visitor totals for actual restaurants from the Kaggle
Recruit Restaurant dataset. Full citations, download links, and column
schemas are in `backend/data/README.md`.

Check it's working: open http://127.0.0.1:8000/docs — you should see the
interactive API docs (Swagger UI) with all endpoints listed.

## 2. Run the frontend

No build step needed — it's plain HTML/JS. Simplest way to serve it:

```bash
cd frontend
python -m http.server 5500
```

Then open:
- **Dashboard:** http://127.0.0.1:5500/index.html
- **Kiosk display for location 1:** http://127.0.0.1:5500/display.html?location=1

(Opening `index.html` directly by double-clicking the file also works in most
browsers, since it just calls the API at `http://127.0.0.1:8000`.)

## 3. (Optional) Run the real computer-vision counter

Once you're ready to log real crowd counts from a webcam:

```bash
cd backend
pip install ultralytics opencv-python requests --break-system-packages
python cv_logger.py --location-id 1 --source 0 --show
```

This runs YOLOv8 (pretrained, downloads automatically on first run) against
your webcam, counts people in frame, and posts the count to the backend
every 60 seconds. Point it at a queue/entrance for a realistic pilot.

## 4. Deploy a physical display board (optional, for your demo)

Any old laptop or a Raspberry Pi connected to a monitor works:

1. Connect the monitor via HDMI.
2. Open Chrome/Chromium in kiosk mode pointed at your display URL:
   ```bash
   chromium-browser --kiosk http://<your-backend-ip>:5500/display.html?location=1
   ```
3. If using a Raspberry Pi, add that command to autostart so it launches on
   boot: `~/.config/lxsession/LXDE-pi/autostart`.

Replace `127.0.0.1` with your machine's actual IP address in both
`index.html`/`display.html` (the `API_BASE` constant) and the kiosk command,
if the display device is a separate machine from the one running the backend.

## API endpoints reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/locations` | List all locations with current status |
| GET | `/api/status/{id}` | Current status for one location |
| POST | `/api/log-count` | CV/IoT script logs a fresh people count |
| POST | `/api/report` | User self-reports a wait time |
| GET | `/api/history/{id}` | Average people count by hour (for charts) |
| GET | `/api/predict/{id}?hour=&day_of_week=` | Predicted rush level for a given time |
| POST | `/api/locations` | Add a new location |

## Upgrading the prediction model

Right now `/api/predict` uses simple historical averaging grouped by
hour + day-of-week — good enough to demo and easy to explain in a viva.
Once you've logged a few weeks of real data, swap the averaging logic in
`main.py`'s `predict()` function for a trained scikit-learn classifier
(e.g. Random Forest on hour, day-of-week, holiday-flag → Low/Medium/High)
without changing the API contract the frontend relies on.
