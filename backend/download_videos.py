"""
CCTV Sample Video Downloader
Downloads free queue/crowd sample videos for the Smart Queue CV pipeline.
Videos are sourced from public domain / Creative Commons sources.
"""

import os
import urllib.request
from pathlib import Path

# â”€â”€â”€ Directory Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
VIDEOS_DIR = Path(__file__).parent / "data" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# â”€â”€â”€ Public Domain / Free Sample Videos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are direct MP4 links from public sources (no API key needed)
SAMPLE_VIDEOS = [
    {
        "name": "hospital_queue.mp4",
        "url": "https://www.pexels.com/download/video/855282/",
        "description": "People walking in corridor / waiting area",
        "location_id": 1,   # Maps to Hospital in our DB
    },
    {
        "name": "mall_crowd.mp4",
        "url": "https://www.pexels.com/download/video/3770806/",
        "description": "Shopping mall crowd footage",
        "location_id": 11,  # Maps to Shopping Mall
    },
    {
        "name": "street_queue.mp4",
        "url": "https://www.pexels.com/download/video/2795750/",
        "description": "People walking on street / public area",
        "location_id": 9,   # Maps to Bus Station
    },
]

# â”€â”€â”€ Fallback: OpenCV built-in test video â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# If downloads fail, we generate a synthetic crowd video using OpenCV
FALLBACK_VIDEOS = [
    {
        "name": "queue_sample_1.mp4",
        "description": "Synthetic queue simulation (Hospital)",
        "location_id": 1,
        "people_range": (5, 25),    # Simulate 5-25 people
    },
    {
        "name": "queue_sample_2.mp4",
        "description": "Synthetic crowd simulation (Mall)",
        "location_id": 11,
        "people_range": (20, 60),
    },
    {
        "name": "queue_sample_3.mp4",
        "description": "Synthetic queue simulation (Bank)",
        "location_id": 7,
        "people_range": (3, 15),
    },
    {
        "name": "queue_sample_4.mp4",
        "description": "Synthetic crowd simulation (Railway Station)",
        "location_id": 8,
        "people_range": (30, 80),
    },
]


def download_video(url: str, save_path: Path) -> bool:
    """Download a video from URL with progress."""
    try:
        print(f"  Downloading: {save_path.name} ...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(save_path, "wb") as f:
                while chunk := response.read(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  Progress: {pct:.1f}%", end="", flush=True)
        print(f"\n  âœ… Saved: {save_path}")
        return True
    except Exception as e:
        print(f"\n  âš ï¸  Download failed: {e}")
        return False


def generate_synthetic_video(save_path: Path, people_range: tuple,
                              duration_sec: int = 30, fps: int = 10):
    """
    Generate a synthetic CCTV-style video with moving dots simulating people.
    Used as fallback when internet download fails.
    """
    import cv2
    import numpy as np
    import random

    print(f"  Generating synthetic video: {save_path.name} ...")

    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(save_path), fourcc, fps, (width, height))

    # Simulate people as moving blobs
    n_people = random.randint(*people_range)
    people = []
    for _ in range(n_people):
        people.append({
            "x": random.randint(30, width - 30),
            "y": random.randint(30, height - 30),
            "vx": random.uniform(-2, 2),
            "vy": random.uniform(-1, 1),
            "size": random.randint(12, 22),
            "color": (
                random.randint(50, 200),
                random.randint(50, 200),
                random.randint(50, 200)
            )
        })

    total_frames = duration_sec * fps
    for frame_idx in range(total_frames):
        # Dark grey background (CCTV-style)
        frame = np.full((height, width, 3), 40, dtype=np.uint8)

        # Draw grid lines (floor tiles simulation)
        for x in range(0, width, 80):
            cv2.line(frame, (x, 0), (x, height), (55, 55, 55), 1)
        for y in range(0, height, 80):
            cv2.line(frame, (0, y), (width, y), (55, 55, 55), 1)

        # Add some people variation over time
        if frame_idx % (fps * 5) == 0:
            # Every 5 seconds: add/remove a person
            if random.random() > 0.5 and len(people) < people_range[1]:
                people.append({
                    "x": random.randint(30, width - 30),
                    "y": random.randint(30, height - 30),
                    "vx": random.uniform(-2, 2),
                    "vy": random.uniform(-1, 1),
                    "size": random.randint(12, 22),
                    "color": (
                        random.randint(50, 200),
                        random.randint(50, 200),
                        random.randint(50, 200)
                    )
                })
            elif len(people) > people_range[0]:
                people.pop(random.randint(0, len(people) - 1))

        # Update and draw each person
        for p in people:
            p["x"] = max(p["size"], min(width - p["size"],
                                        p["x"] + p["vx"]))
            p["y"] = max(p["size"], min(height - p["size"],
                                        p["y"] + p["vy"]))
            if p["x"] <= p["size"] or p["x"] >= width - p["size"]:
                p["vx"] *= -1
            if p["y"] <= p["size"] or p["y"] >= height - p["size"]:
                p["vy"] *= -1

            # Draw person as filled circle with outline (overhead view)
            cv2.circle(frame, (int(p["x"]), int(p["y"])),
                       p["size"], p["color"], -1)
            cv2.circle(frame, (int(p["x"]), int(p["y"])),
                       p["size"], (200, 200, 200), 1)

        # Overlay: timestamp + count
        ts = f"CAM-01  {frame_idx // fps:02d}s  People: {len(people)}"
        cv2.putText(frame, ts, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.putText(frame, "SMART QUEUE CCTV", (width - 220, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        out.write(frame)

    out.release()
    print(f"  âœ… Generated: {save_path} ({total_frames} frames, {len(people)} people)")
    return True


def main():
    print("=" * 60)
    print("  Smart Queue â€” CCTV Video Downloader")
    print("=" * 60)
    print(f"  Save directory: {VIDEOS_DIR}\n")

    video_manifest = []

    # Try downloading real videos first, fallback to synthetic
    print("Phase 1: Attempting to download real CCTV sample videos...\n")
    real_downloaded = 0
    for v in SAMPLE_VIDEOS:
        save_path = VIDEOS_DIR / v["name"]
        if save_path.exists() and save_path.stat().st_size > 10000:
            print(f"  âœ… Already exists: {v['name']}")
            video_manifest.append({**v, "path": str(save_path), "type": "real"})
            real_downloaded += 1
            continue
        if download_video(v["url"], save_path):
            video_manifest.append({**v, "path": str(save_path), "type": "real"})
            real_downloaded += 1

    print(f"\nPhase 2: Generating synthetic CCTV videos as dataset...\n")
    for v in FALLBACK_VIDEOS:
        save_path = VIDEOS_DIR / v["name"]
        if save_path.exists() and save_path.stat().st_size > 1000:
            print(f"  âœ… Already exists: {v['name']}")
            video_manifest.append({**v, "path": str(save_path), "type": "synthetic"})
            continue
        generate_synthetic_video(
            save_path,
            people_range=v["people_range"],
            duration_sec=30,
            fps=10
        )
        video_manifest.append({**v, "path": str(save_path), "type": "synthetic"})

    # Save manifest
    import json
    manifest_path = VIDEOS_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(video_manifest, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  âœ… Ready! {len(video_manifest)} videos prepared.")
    print(f"  ðŸ“„ Manifest: {manifest_path}")
    print(f"  ðŸ“‚ Videos folder: {VIDEOS_DIR}")
    print(f"{'=' * 60}")
    print("\n  Now run: python cv_pipeline.py")


if __name__ == "__main__":
    main()

