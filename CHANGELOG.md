# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
