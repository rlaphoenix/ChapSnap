import json
import re
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
    chapter_list = []
    try:
        tree = ElementTree.parse(file)
    except ElementTree.ParseError:
        data = file.read_text(encoding="utf8")
        line_1_re = re.compile(r"^CHAPTER(?P<number>\d+)=(?P<timestamp>[\d\\.:]+)$")
        line_2_re = re.compile(r"^CHAPTER(?P<number>\d+)NAME=(?P<name>[\d\\.:]+)$")
        lines = [x.strip() for x in data.strip().splitlines()]
        chapter_lines = zip(lines[::2], lines[1::2])
        for line_1, line_2 in chapter_lines:
            one_m = line_1_re.match(line_1)
            two_m = line_2_re.match(line_2)
            if not one_m or not two_m:
                raise SyntaxError(f"An unexpected syntax error near:\n{line_1}\n{line_2}")

            line_1_number, timestamp = one_m.groups()
            line_2_number, name = two_m.groups()
            if line_1_number != line_2_number:
                raise SyntaxError(f"The chapter numbers ({line_1_number},{line_2_number}) do not match.")
            if not timestamp:
                raise SyntaxError(f"The timecode is missing from Chapter {line_1_number}.")

            chapter_list.append((timestamp, name))
    else:
        root = tree.getroot()
        edition = root.find("EditionEntry")
        for chapter in edition.findall("ChapterAtom"):
            timestamp = chapter.find("ChapterTimeStart").text
            name = chapter.find("ChapterDisplay").find("ChapterString").text
            chapter_list.append((timestamp, name))

    return [
        {
            "start_time": timestamp_to_seconds(timestamp),
            "tags": {
                "title": name
            }
        }
        for timestamp, name in chapter_list
    ]


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
                ",".join([
                    x.replace(",", "\\,").replace("'", "\\'")
                    for x in (
                        f"movie='{video_path.as_posix()}'",
                        f"select=gt(scene,{threshold})"
                    )
                ])
            ],
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, _ = p.communicate()
        cache_path.write_text(stdout, encoding="utf8")

    scene_changes = json.loads(stdout)
    scene_changes = scene_changes["frames"]

    return scene_changes


def set_chapters(video_path: Path, chapters_path: Path) -> int:
    return subprocess.check_call([
        "mkvpropedit",
        video_path,
        "--chapters", "",
        "--chapters", chapters_path
    ])
