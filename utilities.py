import json
import subprocess
from datetime import timedelta, datetime
from pathlib import Path
from typing import Any


def format_timestamp(duration_seconds: float) -> str:
    """Convert Seconds to a HH:MM:SS.mss Timestamp string."""
    delta = timedelta(seconds=duration_seconds)
    return (datetime.min + delta).strftime("%H:%M:%S.%f")[:-3]


def get_chapters(video_path: Path) -> list[dict[str, Any]]:
    """Get Video Chapter Timestamps and Names via ffprobe."""
    p = subprocess.Popen(
        [
            "ffprobe",
            "-v", "quiet",
            "-show_chapters",
            "-of", "json",
            video_path
        ],
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, _ = p.communicate()

    chapters = json.loads(stdout)
    chapters = chapters["chapters"]

    return chapters


def get_scene_changes(video_path: Path, threshold: float) -> list[dict[str, Any]]:
    """Get Timestamps of Scene Changes with Frame Information via ffprobe."""
    cache_path = video_path.with_suffix(f"{video_path.suffix}.scene_changes_{threshold}t.json")

    if cache_path.exists():
        stdout = cache_path.read_text(encoding="utf8")
    else:
        p = subprocess.Popen(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_frames",
                "-of", "json",
                "-f", "lavfi",
                f"movie=\\'{video_path.as_posix()}\\',select=gt(scene\\,{threshold})"
            ],
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, _ = p.communicate()
        cache_path.write_text(stdout, encoding="utf8")

    scene_changes = json.loads(stdout)
    scene_changes = scene_changes["frames"]

    return scene_changes


def mux_chapters(video_path: Path, chapters_path: Path, out_path: Path) -> int:
    return subprocess.check_call([
        "mkvmerge",
        "-o", out_path,
        "--chapters", chapters_path,
        video_path
    ])
