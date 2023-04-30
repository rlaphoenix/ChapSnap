# ChapSnap

Resync Chapters by snapping them to Scene Changes.

## Usage

```
Usage: chapsnap [OPTIONS] VIDEO [CHAPTERS]

  Snap Chapters to Scene Changes.

  VIDEO       The video file to snap chapters to scene changes. All video formats are
              supported. You may alternatively provide a directory path to process
              video files in batch.
  [CHAPTERS]  Optional chapters file if you want to use chapters from a file
              rather than ones already muxed with the video.

Options:
  -t, --threshold FLOAT  Threshold on Scene Change probability scores. The
                         lower the value, the more unlikely the frame is to be
                         a Scene Change. Range: 0.0 (Impossible) - 1.0
                         (Definite).
  -o, --offset FLOAT     Offset to apply to each Chapter. A negative offset
                         may result in fewer Chapters.
  --trim INTEGER         Remove n Chapters from the start of the Video. A
                         negative value will remove n Chapters from the end of
                         the Video. Timestamps will be offset respectively.
  -nf, --no-forward      Do not try to resync Chapters forward in time.
  -nb, --no-backward     Do not try to resync Chapters backward in time.
  -k, --keyframes        Only sync to Scene Changes on Keyframes (I-frames).
  -0, --zero             Force the first chapter to be at `00:00:00.000`, even
                         after offsets and trims.
  -c, --chain            Chain sync adjustments from one Chapter to the next.
                         E.g., Chapter 1 had -2, so Chapter 2 will begin with
                         an offset of -2. Chapter 2 with -2 has a change of
                         -1, so Chapter 3 will begin with an offset of -3 and
                         so on.
  --overwrite            Apply new Chapters to the input video file in-place,
                         without making a duplicate.
  --help                 Show this message and exit.
```

## Contributors

<a href="https://github.com/rlaphoenix"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/17136956?v=4&h=25&w=25&fit=cover&mask=circle&maxage=7d" alt=""/></a>

## License

© 2023 rlaphoenix — [GNU General Public License, Version 3.0](LICENSE)
