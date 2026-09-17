# Real-world dataset used by Smart Queue

## Public / commercial foot traffic — City of Melbourne Pedestrian Counting System

**What it is:** Real hourly pedestrian counts from sensors installed at
named public and commercial locations across Melbourne, Australia —
retail malls (Bourke Street Mall, Melbourne Central), transit precincts
(Flinders Street Station), public squares (Birrarung Marr, Town Hall),
and shopping strips. Collected continuously since May 2009 by the City
of Melbourne's automated sensor network. This is the same dataset used
in multiple published forecasting papers (Monash Time Series
Forecasting Archive, MONSTER benchmark).

**Why it fits this project:** It's genuine footfall data at real
public/commercial locations, with an hourly timestamp — the same shape
of data your CV camera pipeline will eventually produce, so it's a
realistic stand-in for training and demoing the prediction model before
your own pilot camera has logged enough data.

**Columns:** `Date_Time, Year, Month, Mdate, Day, Time, Sensor_ID, Sensor_Name, Hourly_Counts`

**Sources (any one of these works — pick whichever downloads easiest for you):**

1. **Official live source** — City of Melbourne Open Data Portal
   https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-counting-system-monthly-counts-per-hour/
   (click "Export" → CSV — updated monthly, largest file, real-time-ish)

2. **Permanent citable mirror (recommended for a capstone report)** — Zenodo, DOI-backed,
   published by Monash University researchers:
   https://zenodo.org/records/4656626
   ("Melbourne Pedestrian Counts Dataset", 66 sensors, CC BY 4.0 license)
   Citation: Godahewa et al., Monash Time Series Forecasting Archive, 2020.

3. **Kaggle mirror** (easiest if you already have a Kaggle account):
   https://www.kaggle.com/datasets/aadimator/melbourne-pedestrian-counting-system-monthly

Download any one, unzip it, and place the CSV at:
```
backend/data/pedestrian_counts.csv
```

Then run:
```bash
cd backend
python load_melbourne_data.py --days 60 --sensors "Bourke Street Mall (North)" "Melbourne Central" "Birrarung Marr"
```

This creates one Smart Queue "location" per selected sensor and loads
its real hourly counts into `crowd_logs`, so `/api/history` and
`/api/predict` immediately reflect real footfall patterns instead of
synthetic data.

## Restaurant / commercial dining — Recruit Restaurant Visitor Forecasting (Kaggle)

**What it is:** Real daily visitor counts for ~800 actual restaurants
in Japan, from the Recruit Holdings reservation + point-of-sale system.
https://www.kaggle.com/competitions/recruit-restaurant-visitor-forecasting/data
(file needed: `air_visit_data.csv` — requires a free Kaggle account to download)

**Important honesty note:** this dataset gives real **daily totals**,
not hourly counts (restaurants don't publish hour-by-hour occupancy
publicly). `load_restaurant_data.py` distributes each real daily total
across hours using a realistic lunch/dinner-peak shape, so the *daily*
number is real data, and the *hourly* breakdown is a modeled estimate.
Mention this distinction if asked about it in your viva — it's exactly
the kind of honest data-limitation discussion evaluators like to see.

Download `air_visit_data.csv`, place it at `backend/data/air_visit_data.csv`, then run:
```bash
cd backend
python load_restaurant_data.py --restaurants 3
```
