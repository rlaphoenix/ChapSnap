# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2023-04-30

### Added

- You can now provide a directory as the primary argument, and it will run on all video files within that
  directory, recursively. It uses MediaInfo to check if the file is a valid video file.
- Implemented `--trim`, a way to remove chapters while offsetting timecodes. It can trim from the start or
  end of the video. A positive value will be from the start, and a negative value will be from the end.
- Implemented `--overwrite` to allow you to apply the new chapters to the original input MKV file instead of
  duplicating it beforehand.
- Implemented `-0/--zero` to force the first Chapter to have a timestamp of `00:00:00.000`, no matter what.
  This is useful when combined with `--offset` but you want the first timestamp to still be zero, or if you
  want to fix slightly incorrect beginning Chapters. Do note that if the first Chapter is unexpectedly offset,
  then you may want to instead use `--offset` with a negative value instead.
- Implemented `-c/--chain` to chain sync adjustments to the next Chapter. This can be useful if you are expecting
  each chapter to go backward in time, and not forward. E.g., if you used Chapters from a Source that is longer,
  and the difference in duration occurred at every Chapter marker.

### Changed

- The change made to Chapter timecodes when using `--offset` will now apply after loading the Chapters, not
  directly before syncing to scenes. This way the Chapter List will now show the change.
- The offset value as specified with `--offset` is now listed under the Chapter list.
- The `mkvpropedit` executable from the MKVToolNix Suite is now used when applying the Chapters to MKV files
  instead of `mkvmerge` to reduce the amount of time taken by quite a bit. It also reduces the amount of read/
  writes to basically nothing.

### Fixed

- Pre-existing Chapters in MKV files are now correctly overwritten when adding the newly synced chapters back
  to the MKV file instead of appending them to the pre-existing chapters.
- Fixed some edge-cases where Chapters with their timestamp as their name was not updated after the timestamp
  was synced or modified.
- Fixed a crash that occurred if the Chapter Name was not a Timestamp string.

## [1.1.0] - 2023-04-26

### Added

- New Chapters will now be automatically muxed into the input file. The input file must be an MKV file.
- Implemented `-k/--keyframes` to only sync to Scene Changes on Key Frames.
- Chapters can now be sourced from a file as an alternative to loading them from the input video. This is
  convenient when you don't want to use the chapters within the input video file, or if there's no chapters
  within it. It supports both XML and Simple text formats.

### Changed

- Replaced the debugging prints listing the before/after timestamp (in seconds) and the closest scene changes
  with a Rich Table with information in a more readable format. Chapters that were removed because they matched
  a previous chapter are now marked as such in the table.
- The new matroska chapters text data is no longer printed. It's now unnecessary to be printed as the new Rich
  Table has all the information you need. If you still need to see the new chapters text, just open the saved
  `.retimed_chapters.txt` file next to the input file.

### Removed

- The `-nr/--no-resync` flag was removed as it didn't actually do anything or have purpose. It was intended to
  stop resyncing chapters that were already synced to a Scene Change. However, the code never did this in the
  first place nor do I want it to.

### Fixed

- Fixed double-dot in the output chapters file (i.e. `video..retimed_chapters.txt`).

## [1.0.0] - 2023-04-26

Initial release.

[1.1.0]: https://github.com/rlaphoenix/ChapSnap/releases/tag/v1.1.0
[1.0.0]: https://github.com/rlaphoenix/ChapSnap/releases/tag/v1.0.0
