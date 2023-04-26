import json
import subprocess
from datetime import timedelta, datetime
from functools import partial
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def format_timestamp(duration_seconds: float) -> str:
    """Convert Seconds to a HH:MM:SS.mss Timestamp string."""
    delta = timedelta(seconds=duration_seconds)
    return (datetime.min + delta).strftime("%H:%M:%S.%f")[:-3]


def timestamp_to_seconds(timestamp: str) -> float:
    """Convert a HH:MM:SS.mss Timestamp to Seconds."""
    h, m, s = timestamp.split(":")
    s, ms = s.split(".")
    total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    return total_seconds


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


def load_chapters_file(file: Path) -> list[dict[str, Any]]:
    tree = ElementTree.parse(file)
    root = tree.getroot()

    edition = root.find("EditionEntry")

    chapter_list = []
    for chapter in edition.findall("ChapterAtom"):
        start_time = chapter.find("ChapterTimeStart").text
        name = chapter.find("ChapterDisplay").find("ChapterString").text

        start_time = timestamp_to_seconds(start_time)

        chapter_list.append({
            "start_time": start_time,
            "tags": {
                "title": name
            }
        })

    return chapter_list


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


def mux_chapters(video_path: Path, chapters_path: Path, out_path: Path, progress: partial) -> int:
    p = subprocess.Popen([
        "mkvmerge",
        video_path,
        "--output", out_path,
        "--chapters", chapters_path,
        "--gui-mode"
    ], text=True, stdout=subprocess.PIPE)

    for line in iter(p.stdout.readline, ""):
        if "progress" in line:
            progress(total=100, completed=int(line.strip()[14:-1]))

    return p.wait()
