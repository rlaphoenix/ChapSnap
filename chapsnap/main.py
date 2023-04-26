from __future__ import annotations

from datetime import datetime
from functools import partial
from pathlib import Path

import click
from rich.status import Status
from rich.table import Table
from rich.progress import Progress
from rich.progress import TextColumn, SpinnerColumn, BarColumn, TimeRemainingColumn
from rich import print

from utilities import get_chapters, get_scene_changes, format_timestamp, mux_chapters


@click.command(help="Snap Chapters to Scene Changes.")
@click.argument("video", type=Path)
@click.option("-t", "--threshold", type=float, default=0.4,
              help="Threshold on Scene Change probability scores. The lower the value, the more unlikely the "
                   "frame is to be a Scene Change. Range: 0.0 (Impossible) - 1.0 (Definite).")
@click.option("-o", "--offset", type=float, default=None,
              help="Offset to apply to each Chapter. A negative offset may result in fewer Chapters.")
@click.option("-nf", "--no-forward", is_flag=True, default=False,
              help="Do not try to resync Chapters forward in time.")
@click.option("-nb", "--no-backward", is_flag=True, default=False,
              help="Do not try to resync Chapters backward in time.")
@click.option("-nr", "--no-resync", is_flag=True, default=False,
              help="Do not try to resync Chapters that are already synced.")
@click.option("-k", "--keyframes", is_flag=True, default=False,
              help="Only sync to Scene Changes on Keyframes (I-frames).")
def main(
    video: Path,
    threshold: float,
    offset: float | None,
    no_forward: bool,
    no_backward: bool,
    no_resync: bool,
    keyframes: bool
):
    if offset is not None and not isinstance(offset, float):
        raise click.ClickException(f"Expected offset to be a {float} not {offset!r}")

    with Status("Getting Chapters..."):
        chapters = get_chapters(video)
        chapter_table = Table(title="Chapters")
        chapter_table.add_column("#", justify="right")
        chapter_table.add_column("Name")
        chapter_table.add_column("Timestamp")
        for i, chapter in enumerate(chapters, start=1):
            name = chapter.get("tags", {}).get("title")
            timestamp = format_timestamp(float(chapter["start_time"]))
            chapter_table.add_row(f"{i:02}", name or "—", timestamp)
        print(chapter_table)

    with Status("Analyzing Video for Scene Changes (this could take a while)..."):
        scene_changes = get_scene_changes(video, threshold)
        scene_change_table = Table(title="Scene Changes")
        scene_change_table.add_column("#", justify="right")
        scene_change_table.add_column("Timestamp")
        scene_change_table.add_column("Type")
        scene_change_table.add_column("Score")
        for i, scene_change in enumerate(scene_changes, start=1):
            timestamp = format_timestamp(float(scene_change["best_effort_timestamp_time"]))
            scene_change_table.add_row(
                f"{i:02}",
                timestamp,
                scene_change["pict_type"],
                scene_change["tags"]["lavfi.scene_score"]
            )
        print(scene_change_table)

    new_chapter_timestamps = {}

    for i, chapter in enumerate(chapters, start=1):
        start_time = float(chapter["start_time"])
        if offset:
            start_time = max(start_time + offset, 0)

        name = chapter.get("tags", {}).get("title")

        if no_resync:
            is_already_timed = any(float(x["best_effort_timestamp_time"]) == start_time for x in scene_changes)
        else:
            is_already_timed = False

        if is_already_timed:
            print(f"- Chapter {i} ({start_time})", "is already synced to a Scene Change")
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

            print(f"- Chapter {i} ({start_time})", closest, f"{closest_forward} (Forward)",
                  f"{closest_backward} (Backward)")
            start_time = closest

            if datetime.strptime(name, "%H:%M:%S.%f"):
                name = format_timestamp(start_time)

        new_chapter_timestamps[start_time] = name

    new_chapter_file = "\n".join([
        line
        for i, (timestamp, name) in enumerate(new_chapter_timestamps.items(), start=1)
        for line in [
            f"CHAPTER{i:02}={format_timestamp(timestamp)}",
            f"CHAPTER{i:02}NAME={name or f'Chapter {i:02}'}"
        ]
    ])
    print(new_chapter_file)

    chapters_file_path = video.with_suffix(f"{video.suffix}.retimed_chapters.txt")
    chapters_file_path.write_text(new_chapter_file, encoding="utf8")

    muxing_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(finished_text=""),
        BarColumn(),
        "•",
        TimeRemainingColumn(compact=True, elapsed_when_finished=True)
    )

    with muxing_progress:
        task = muxing_progress.add_task("Multiplexing...", total=100, start=True)
        out_path = video.with_stem(video.stem + " (Resynced)")
        mux_chapters(
            video,
            chapters_file_path,
            out_path,
            progress=partial(muxing_progress.update, task_id=task)
        )

    print(":tada: Done!")


if __name__ == "__main__":
    main()
