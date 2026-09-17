"""
Computer-vision people counter that logs live counts to the Smart Queue API.

Runs YOLOv8 (pretrained "person" class) against a webcam or video file and
POSTs the count to /api/log-count every LOG_INTERVAL_SECONDS.

Install first (not in requirements.txt since it's heavy and optional):
    pip install ultralytics opencv-python requests --break-system-packages

Run with:
    python cv_logger.py --location-id 1 --source 0          # webcam
    python cv_logger.py --location-id 1 --source video.mp4  # video file
"""

import argparse
import time

import cv2
import requests
from ultralytics import YOLO

API_BASE = "http://127.0.0.1:8000"
LOG_INTERVAL_SECONDS = 60


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--location-id", type=int, required=True)
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--show", action="store_true", help="Show a preview window")
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    model = YOLO("yolov8n.pt")  # downloads automatically on first run
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    last_log_time = 0

    print(f"Logging location {args.location_id} to {API_BASE} every {LOG_INTERVAL_SECONDS}s. Ctrl+C to stop.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            results = model(frame, classes=[0], verbose=False)  # class 0 = person in COCO
            person_count = len(results[0].boxes)

            if args.show:
                annotated = results[0].plot()
                cv2.putText(annotated, f"Count: {person_count}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Smart Queue - CV Logger", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            now = time.time()
            if now - last_log_time >= LOG_INTERVAL_SECONDS:
                try:
                    requests.post(
                        f"{API_BASE}/api/log-count",
                        json={"location_id": args.location_id, "people_count": person_count, "source": "cv"},
                        timeout=5,
                    )
                    print(f"Logged count={person_count}")
                except requests.RequestException as e:
                    print(f"Failed to log to API: {e}")
                last_log_time = now

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
