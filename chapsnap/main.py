from __future__ import annotations

from datetime import datetime
from functools import partial
from pathlib import Path

import click
from rich.status import Status
from rich.table import Table, Column
from rich.progress import Progress
from rich.progress import TextColumn, SpinnerColumn, BarColumn, TimeRemainingColumn
from rich import print

from utilities import get_chapters, get_scene_changes, format_timestamp, mux_chapters, load_chapters_file


@click.command()
@click.argument("video", type=Path)
@click.argument("chapters", type=Path, required=False)
@click.option("-t", "--threshold", type=float, default=0.4,
              help="Threshold on Scene Change probability scores. The lower the value, the more unlikely the "
                   "frame is to be a Scene Change. Range: 0.0 (Impossible) - 1.0 (Definite).")
@click.option("-o", "--offset", type=float, default=None,
              help="Offset to apply to each Chapter. A negative offset may result in fewer Chapters.")
@click.option("-nf", "--no-forward", is_flag=True, default=False,
              help="Do not try to resync Chapters forward in time.")
@click.option("-nb", "--no-backward", is_flag=True, default=False,
              help="Do not try to resync Chapters backward in time.")
@click.option("-k", "--keyframes", is_flag=True, default=False,
              help="Only sync to Scene Changes on Keyframes (I-frames).")
def main(
    video: Path,
    chapters: Path | None,
    threshold: float,
    offset: float | None,
    no_forward: bool,
    no_backward: bool,
    keyframes: bool
):
    """
    Snap Chapters to Scene Changes.

    \b
    VIDEO       The video file to snap chapters to scene changes.
    [CHAPTERS]  Optional chapters file if you want to use chapters from a file
                rather than ones already muxed with the video.
    """
    if offset is not None and not isinstance(offset, float):
        raise click.ClickException(f"Expected offset to be a {float} not {offset!r}")

    with Status("Getting Chapters..."):
        if chapters:
            chapters = load_chapters_file(chapters)
        else:
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
        if offset:
            start_time = max(start_time + offset, 0)

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
