from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import click
from rich.status import Status
from rich.table import Table, Column
from rich import print
from pymediainfo import MediaInfo

from utilities import get_chapters, get_scene_changes, format_timestamp, load_chapters_file, set_chapters


@click.command()
@click.argument("video", type=Path)
@click.argument("chapters", type=Path, required=False)
@click.option("-t", "--threshold", type=float, default=0.4,
              help="Threshold on Scene Change probability scores. The lower the value, the more unlikely the "
                   "frame is to be a Scene Change. Range: 0.0 (Impossible) - 1.0 (Definite).")
@click.option("-o", "--offset", type=float, default=None,
              help="Offset to apply to each Chapter. A negative offset may result in fewer Chapters.")
@click.option("--trim", type=int, multiple=True, default=None,
              help="Remove n Chapters from the start of the Video. A negative value will remove n Chapters from"
                   "the end of the Video. Timestamps will be offset respectively.")
@click.option("-nf", "--no-forward", is_flag=True, default=False,
              help="Do not try to resync Chapters forward in time.")
@click.option("-nb", "--no-backward", is_flag=True, default=False,
              help="Do not try to resync Chapters backward in time.")
@click.option("-k", "--keyframes", is_flag=True, default=False,
              help="Only sync to Scene Changes on Keyframes (I-frames).")
@click.option("--overwrite", is_flag=True, default=False,
              help="Apply new Chapters to the input video file in-place, without making a duplicate.")
def main(
    video: Path,
    chapters: Path | None,
    threshold: float,
    offset: float | None,
    trim: list[int],
    no_forward: bool,
    no_backward: bool,
    keyframes: bool,
    overwrite: bool
):
    """
    Snap Chapters to Scene Changes.

    \b
    VIDEO       The video file to snap chapters to scene changes. All video formats are
                supported. You may alternatively provide a directory path to process
                video files in batch.
    [CHAPTERS]  Optional chapters file if you want to use chapters from a file
                rather than ones already muxed with the video.
    """
    if offset is not None and not isinstance(offset, float):
        raise click.ClickException(f"Expected offset to be a {float} not {offset!r}")

    chapters_ = chapters

    if video.is_file():
        videos = [video]
    else:
        videos = [
            x
            for x in video.glob("**/*.*")
            if not x.stem.endswith(" (Resynced)") and MediaInfo.parse(x).video_tracks
        ]

    for video in videos:
        print(f"Processing {video.stem}...")
        with Status("Getting Chapters..."):
            if chapters_:
                chapters = load_chapters_file(chapters_)
            else:
                chapters = get_chapters(video)
            if trim:
                for amount in trim:
                    negative = amount < 0
                    trim_offset = float(chapters[amount]["start_time"]) - float(chapters[amount - 1]["start_time"])
                    if negative:
                        chapters = chapters[:amount]
                    else:
                        chapters = chapters[amount:]
                    for chapter in chapters:
                        chapter["start_time"] = float(chapter["start_time"]) - trim_offset
                        name = chapter.get("tags", {}).get("title")
                        if name and datetime.strptime(name, "%H:%M:%S.%f"):
                            chapter["tags"]["title"] = format_timestamp(chapter["start_time"])
            if offset:
                for chapter in chapters:
                    chapter["start_time"] = max(float(chapter["start_time"]) + offset, 0)

            chapter_table = Table(
                Column("#", justify="right"),
                "Name",
                "Timestamp",
                title="Chapters",
                caption=f"offset: {offset:.3f}" if offset else None,
                caption_justify="right"
            )
            for i, chapter in enumerate(chapters, start=1):
                name = chapter.get("tags", {}).get("title")
                timestamp = format_timestamp(float(chapter["start_time"]))
                chapter_table.add_row(f"{i:02}", name or "—", timestamp)
            print(chapter_table)

        with Status("Analyzing Video for Scene Changes (this could take a while)..."):
            scene_changes = get_scene_changes(video, threshold)
            scene_change_table = Table(
                Column("#", justify="right"),
                "Timestamp",
                "Type",
                "Score",
                title="Scene Changes"
            )
            for i, scene_change in enumerate(scene_changes, start=1):
                timestamp = format_timestamp(float(scene_change["best_effort_timestamp_time"]))
                scene_change_table.add_row(
                    f"{i:02}",
                    timestamp,
                    scene_change["pict_type"],
                    scene_change["tags"]["lavfi.scene_score"]
                )
            print(scene_change_table)

        new_chapter_table = Table(
            Column("#", justify="right"),
            "Before",
            "After",
            "Change",
            "Closest Scene Changes",
            title="Chapter Modifications"
        )

        new_chapter_timestamps = {}

        for i, chapter in enumerate(chapters, start=1):
            start_time = float(chapter["start_time"])

            name = chapter.get("tags", {}).get("title")

            is_already_timed = any(float(x["best_effort_timestamp_time"]) == start_time for x in scene_changes)

            if is_already_timed:
                new_chapter_table.add_row(
                    f"{i:02}",
                    format_timestamp(start_time),
                    format_timestamp(start_time),
                    "0.00",
                    "Already synced, skipped..."
                )
            else:
                if no_forward:
                    closest_forward = 0.0
                else:
                    closest_forward = next((
                        float(x["best_effort_timestamp_time"])
                        for x in scene_changes
                        if float(x["best_effort_timestamp_time"]) > start_time and
                        (not keyframes or x["pict_type"] == "I")
                    ), 0.0)

                if no_backward or start_time == 0.0:
                    closest_backward = 0.0
                else:
                    closest_backward = next(
                        float(x["best_effort_timestamp_time"])
                        for x in reversed(scene_changes)
                        if float(x["best_effort_timestamp_time"]) <= start_time and
                        (not keyframes or x["pict_type"] == "I")
                    )

                closest = min((closest_forward, closest_backward), key=lambda x: abs(x - start_time))
                cb = [" ", "*"][closest == closest_backward]
                cf = [" ", "*"][closest == closest_forward]

                if closest in new_chapter_timestamps:
                    new_chapter_table.add_row(
                        "--",
                        format_timestamp(start_time),
                        format_timestamp(closest),
                        f"{closest - start_time:.2f}",
                        "Removed, matched previous chapter"
                    )
                    continue

                new_chapter_table.add_row(
                    f"{i:02}",
                    format_timestamp(start_time),
                    format_timestamp(closest),
                    f"{closest - start_time:.2f}",
                    f"{format_timestamp(closest_backward)}{cb} <- | -> {format_timestamp(closest_forward)}{cf}"
                )

                start_time = closest

                if datetime.strptime(name, "%H:%M:%S.%f"):
                    name = format_timestamp(start_time)

            new_chapter_timestamps[start_time] = name

        print(new_chapter_table)

        new_chapter_file = "\n".join([
            line
            for i, (timestamp, name) in enumerate(new_chapter_timestamps.items(), start=1)
            for line in [
                f"CHAPTER{i:02}={format_timestamp(timestamp)}",
                f"CHAPTER{i:02}NAME={name or f'Chapter {i:02}'}"
            ]
        ])

        chapters_file_path = video.with_suffix(f"{video.suffix}.retimed_chapters.txt")
        chapters_file_path.write_text(new_chapter_file, encoding="utf8")

        if video.suffix.lower() == ".mkv":
            with Status("Updating Chapters in MKV Container..."):
                if overwrite:
                    out_path = video
                else:
                    out_path = video.with_stem(video.stem + " (Resynced)")
                    shutil.copy(video, out_path)
                set_chapters(out_path, chapters_file_path)

    print(":tada: Done!")


if __name__ == "__main__":
    main()
