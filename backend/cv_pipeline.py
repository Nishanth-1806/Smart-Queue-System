"""
Smart Queue — CCTV Computer Vision Pipeline
============================================
Processes CCTV video files to detect and count people,
then pushes crowd counts to the backend API every N seconds.

Supports:
  - YOLOv8  (primary  — high accuracy)
  - HOG     (fallback — no extra model download needed)
  - Synthetic count simulation (demo mode)

Usage:
  python cv_pipeline.py                   # Process all videos in data/videos/
  python cv_pipeline.py --video path.mp4  # Process a single video file
  python cv_pipeline.py --demo            # Demo mode (no video needed)
  python cv_pipeline.py --location 1      # Target specific location ID
"""

import cv2
import time
import json
import random
import argparse
import threading
import requests
from pathlib import Path
from datetime import datetime
from collections import deque

# ─── Config ─────────────────────────────────────────────────────────────────
API_BASE       = "http://127.0.0.1:8000"
PUSH_INTERVAL  = 10          # Push crowd count to API every N seconds
FRAME_SKIP     = 5           # Process every Nth frame (speed vs accuracy)
CONF_THRESHOLD = 0.4         # YOLO confidence threshold
VIDEOS_DIR     = Path(__file__).parent / "data" / "videos"
LOG_DIR        = Path(__file__).parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# YOLO model (downloaded automatically on first use ~6MB)
YOLO_MODEL_SIZE = "yolov8n.pt"   # nano = fastest, good enough for demo

# ─── Detector Setup ──────────────────────────────────────────────────────────

def load_yolo():
    """Load YOLOv8 nano model."""
    try:
        from ultralytics import YOLO
        print("  [YOLO] Loading YOLOv8n model (auto-download if first time)...")
        model = YOLO(YOLO_MODEL_SIZE)
        print("  [YOLO] ✅ Model ready")
        return model
    except ImportError:
        print("  [YOLO] ⚠️  ultralytics not installed — using HOG fallback")
        return None
    except Exception as e:
        print(f"  [YOLO] ⚠️  Load error: {e} — using HOG fallback")
        return None


def load_hog():
    """Load OpenCV HOG person detector (built-in, no download needed)."""
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    print("  [HOG]  ✅ OpenCV HOG detector ready")
    return hog


# ─── Detection Functions ─────────────────────────────────────────────────────

def detect_with_yolo(model, frame):
    """Detect people using YOLOv8. Returns (count, annotated_frame)."""
    results = model(frame, classes=[0], conf=CONF_THRESHOLD, verbose=False)
    count = 0
    annotated = frame.copy()
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            count = len(boxes)
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated, f"{conf:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return count, annotated


def detect_with_hog(hog, frame):
    """Detect people using HOG descriptor. Returns (count, annotated_frame)."""
    # Resize for faster HOG processing
    small = cv2.resize(frame, (320, 240))
    scale = frame.shape[1] / 320

    rects, weights = hog.detectMultiScale(
        small,
        winStride=(8, 8),
        padding=(4, 4),
        scale=1.05,
        useMeanshiftGrouping=False
    )

    annotated = frame.copy()
    count = 0
    for (x, y, w, h), weight in zip(rects, weights):
        if weight > 0.3:
            x1 = int(x * scale)
            y1 = int(y * scale)
            x2 = int((x + w) * scale)
            y2 = int((y + h) * scale)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 165, 0), 2)
            cv2.putText(annotated, f"Person", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)
            count += 1

    return count, annotated


# ─── API Push ────────────────────────────────────────────────────────────────

def push_to_api(location_id: int, count: int, source: str = "cv_pipeline"):
    """Push people count to backend /api/log-count endpoint."""
    try:
        payload = {
            "location_id": location_id,
            "count": count,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        resp = requests.post(
            f"{API_BASE}/api/log-count",
            json=payload,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            wt   = data.get("estimated_wait_minutes", "?")
            rl   = data.get("rush_level", "?")
            print(f"  [API] ✅ Location {location_id}: "
                  f"{count} people | Wait: {wt} min | Status: {rl}")
            return True
        else:
            print(f"  [API] ⚠️  HTTP {resp.status_code}: {resp.text[:80]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [API] ❌ Cannot reach backend at {API_BASE}. Is it running?")
        return False
    except Exception as e:
        print(f"  [API] ❌ Error: {e}")
        return False


# ─── Video Processor ─────────────────────────────────────────────────────────

class VideoProcessor:
    def __init__(self, video_path: str, location_id: int,
                 yolo_model=None, hog_detector=None, show_window: bool = False):
        self.video_path  = video_path
        self.location_id = location_id
        self.yolo        = yolo_model
        self.hog         = hog_detector
        self.show_window = show_window
        self.running     = False
        self.count_history = deque(maxlen=30)  # rolling average window

        # Determine detector name
        if self.yolo:
            self.detector_name = "YOLOv8"
        elif self.hog:
            self.detector_name = "HOG"
        else:
            self.detector_name = "Synthetic"

    def smooth_count(self, raw_count: int) -> int:
        """Return smoothed count using rolling average to avoid flickering."""
        self.count_history.append(raw_count)
        return round(sum(self.count_history) / len(self.count_history))

    def process(self):
        """Main processing loop for a single video file."""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"  ❌ Cannot open video: {self.video_path}")
            return

        fps        = cap.get(cv2.CAP_PROP_FPS) or 10
        total_f    = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_name = Path(self.video_path).name
        self.running = True

        print(f"\n  📹 Processing: {video_name}")
        print(f"     Location ID : {self.location_id}")
        print(f"     Detector    : {self.detector_name}")
        print(f"     FPS         : {fps:.1f}  |  Total frames: {total_f}")
        print(f"     Push every  : {PUSH_INTERVAL}s\n")

        frame_idx     = 0
        last_push_t   = time.time()
        last_count    = 0
        log_entries   = []

        while self.running:
            ret, frame = cap.read()
            if not ret:
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_idx = 0
                continue

            frame_idx += 1

            # Skip frames for performance
            if frame_idx % FRAME_SKIP != 0:
                continue

            # Resize for consistency
            frame = cv2.resize(frame, (640, 480))

            # ── Detect People ──────────────────────────────────────────────
            if self.yolo:
                raw_count, annotated = detect_with_yolo(self.yolo, frame)
            elif self.hog:
                raw_count, annotated = detect_with_hog(self.hog, frame)
            else:
                # Synthetic: simulate crowd fluctuation
                raw_count = max(0, last_count + random.randint(-3, 3))
                annotated = frame.copy()

            last_count = self.smooth_count(raw_count)

            # ── Draw Overlay ───────────────────────────────────────────────
            ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            overlay_lines = [
                f"SMART QUEUE CCTV  |  Loc ID: {self.location_id}",
                f"Detector: {self.detector_name}  |  People: {last_count}",
                f"{ts}",
            ]
            # Dark banner at top
            cv2.rectangle(annotated, (0, 0), (640, 70), (0, 0, 0), -1)
            for i, line in enumerate(overlay_lines):
                color = (0, 255, 0) if i == 1 else (200, 200, 200)
                cv2.putText(annotated, line, (8, 18 + i * 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1)

            # Bottom status bar
            cv2.rectangle(annotated, (0, 455), (640, 480), (0, 0, 0), -1)
            cv2.putText(annotated,
                        f"Frame {frame_idx}/{total_f}  |  Push in: "
                        f"{max(0, PUSH_INTERVAL - int(time.time() - last_push_t))}s",
                        (8, 472), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

            if self.show_window:
                cv2.imshow(f"Smart Queue CCTV — {video_name}", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("  [CV] Stopped by user (Q key)")
                    break

            # ── Push to API ────────────────────────────────────────────────
            now = time.time()
            if now - last_push_t >= PUSH_INTERVAL:
                push_to_api(self.location_id, last_count, self.detector_name)
                log_entries.append({
                    "timestamp": datetime.now().isoformat(),
                    "location_id": self.location_id,
                    "frame": frame_idx,
                    "people_count": last_count,
                    "detector": self.detector_name,
                    "video": video_name
                })
                last_push_t = now

        cap.release()
        if self.show_window:
            cv2.destroyAllWindows()

        # Save log
        log_path = LOG_DIR / f"cv_log_{self.location_id}_{int(time.time())}.json"
        with open(log_path, "w") as f:
            json.dump(log_entries, f, indent=2)
        print(f"  [LOG] Saved {len(log_entries)} entries → {log_path}")


# ─── Multi-Video Runner ───────────────────────────────────────────────────────

def run_all_videos(yolo_model, hog_detector, show_window: bool = False):
    """Process all videos from manifest.json in parallel threads."""
    manifest_path = VIDEOS_DIR / "manifest.json"
    if not manifest_path.exists():
        print("  ❌ No manifest.json found. Run download_videos.py first!")
        return

    with open(manifest_path) as f:
        videos = json.load(f)

    if not videos:
        print("  ❌ No videos in manifest!")
        return

    print(f"\n  Found {len(videos)} video(s) in manifest\n")

    threads = []
    for v in videos:
        vpath = v.get("path", "")
        if not Path(vpath).exists():
            print(f"  ⚠️  Skipping missing file: {vpath}")
            continue

        processor = VideoProcessor(
            video_path=vpath,
            location_id=v.get("location_id", 1),
            yolo_model=yolo_model,
            hog_detector=hog_detector,
            show_window=show_window
        )
        t = threading.Thread(target=processor.process, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.5)  # Stagger starts

    print(f"\n  ▶️  {len(threads)} video processor(s) running...")
    print("  Press Ctrl+C to stop\n")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n  ⛔ Stopped by user")


def run_demo_mode(yolo_model, hog_detector):
    """Demo mode: simulate CV counts for all 18 DB locations without a real video."""
    print("\n  🎭 DEMO MODE — Simulating CCTV counts for all locations\n")

    LOCATION_CONFIGS = {
        1:  (10, 40),   # City General Hospital
        2:  (5,  20),   # St. Mary's Medical Center
        3:  (15, 45),   # LifeCare Multi-Specialty
        4:  (8,  25),   # Sunrise Children's Hospital
        5:  (20, 60),   # SF City Hall
        6:  (10, 30),   # DMV Service Center
        7:  (5,  20),   # Chase Bank Main Branch
        8:  (30, 90),   # SF Central Station
        9:  (20, 70),   # Transbay Transit Center
        10: (5,  15),   # SF International Airport T3
        11: (25, 80),   # Westfield Shopping Mall
        12: (15, 50),   # Golden Gate Mall
        13: (5,  25),   # US Post Office
        14: (10, 40),   # Grand Royal Opera
        15: (5,  20),   # Bella Italia Trattoria
        16: (3,  15),   # Sakura Sushi
        17: (10, 35),   # Smokehouse Grill
        18: (8,  30),   # Pier 39 Seafood
    }

    print(f"  Pushing crowd counts every {PUSH_INTERVAL}s for {len(LOCATION_CONFIGS)} locations\n")
    counts = {loc_id: random.randint(*rng) for loc_id, rng in LOCATION_CONFIGS.items()}

    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"\n  ── Iteration {iteration} ── {datetime.now().strftime('%H:%M:%S')} ──")

            for loc_id, (low, high) in LOCATION_CONFIGS.items():
                # Gradually fluctuate count
                current = counts[loc_id]
                delta   = random.randint(-5, 5)
                counts[loc_id] = max(low, min(high, current + delta))
                push_to_api(loc_id, counts[loc_id], "demo_simulation")
                time.sleep(0.2)  # Small delay between API calls

            print(f"\n  ⏳ Waiting {PUSH_INTERVAL}s before next update...")
            time.sleep(PUSH_INTERVAL)

    except KeyboardInterrupt:
        print("\n  ⛔ Demo mode stopped")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smart Queue CCTV CV Pipeline"
    )
    parser.add_argument("--video",    type=str,  help="Path to a single video file")
    parser.add_argument("--location", type=int,  default=1, help="Location ID for single video")
    parser.add_argument("--demo",     action="store_true",  help="Run demo simulation mode")
    parser.add_argument("--show",     action="store_true",  help="Show OpenCV window (needs display)")
    parser.add_argument("--hog",      action="store_true",  help="Force HOG detector (skip YOLO)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Smart Queue — CCTV CV Pipeline")
    print("=" * 60)
    print(f"  Backend  : {API_BASE}")
    print(f"  Mode     : {'Demo' if args.demo else 'Single video' if args.video else 'All videos'}")
    print()

    # Load detectors
    yolo_model   = None if args.hog else load_yolo()
    hog_detector = load_hog() if (not yolo_model) else None

    # ── Run selected mode ──────────────────────────────────────────────────
    if args.demo:
        run_demo_mode(yolo_model, hog_detector)

    elif args.video:
        if not Path(args.video).exists():
            print(f"  ❌ File not found: {args.video}")
            return
        processor = VideoProcessor(
            video_path=args.video,
            location_id=args.location,
            yolo_model=yolo_model,
            hog_detector=hog_detector,
            show_window=args.show
        )
        processor.process()

    else:
        # Process all videos from manifest
        run_all_videos(yolo_model, hog_detector, show_window=args.show)


if __name__ == "__main__":
    main()
