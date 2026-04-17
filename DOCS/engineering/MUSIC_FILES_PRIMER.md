# Music Files Primer

> What MP3s are, how they store metadata, how audio fingerprinting works,
> and how Shazam identifies a song — explained without jargon.

---

## What is an MP3?

An MP3 file contains two distinct things: the actual audio (the compressed sound data)
and a metadata wrapper that describes what the audio is. The audio is like the contents
of a book — the actual story. The metadata is like the information printed on the cover
and spine: the title, the author, the publisher, the year. You can have one without the
other. A file with great audio and no metadata is a song with no name. A file with
metadata but corrupt audio is a label with nothing inside.

When files are ripped, downloaded, or copied from unknown sources, the audio is usually
intact — but the metadata may be wrong, empty, or completely missing.

---

## What are ID3 tags?

ID3 is the standard metadata format for MP3 files. The tags are a small block of
structured data embedded at the start (or sometimes end) of the MP3 file. Every tag has
a four-letter code that identifies what it contains:

| Tag code | What it stores | Example |
|---|---|---|
| `TIT2` | Song title | `Vaseegara` |
| `TPE1` | Artist name | `Bombay Jayashri` |
| `TALB` | Album name | `Minnale` |
| `TDRC` | Year of release | `2001` |
| `TCON` | Genre | `Tamil` |
| `APIC` | Cover art image | (JPEG bytes, embedded in the file) |
| `TXXX` | Custom free-form field | `PIPELINE_ID: max-000001` |

Every music player — VLC, Apple Music, Windows Media Player, Spotify, car audio systems —
reads these tags to display song information, sort libraries, and show cover art. Without
them, the player has nothing to show except the filename, and displays: "Unknown Artist /
Unknown Album / Track 01."

---

## Why filenames don't matter

ID3 tags are embedded inside the file's bytes. They travel with the file wherever it goes.
Rename the file, move it to another folder, copy it to a USB drive, upload it — the tags
are still there, unchanged, inside the file itself.

This is why the pipeline renames files last (Stage 4). Once the tags are written in Stage
3, the file "knows" what it is regardless of what its filename says. The filename is a
convenience for humans and file browsers — not where the music identity actually lives.

A file called `yt_dl_jkdf8827.mp3` with correct ID3 tags will show up in Apple Music as
"Vaseegara — Bombay Jayashri — Minnale — 2001" with the album cover, correctly sorted.

---

## What is audio fingerprinting?

Audio fingerprinting is like a "sonic photograph" of a piece of audio. An algorithm
analyses the frequency patterns in the sound — which pitches are loud at which moments
across the timeline of the recording — and compresses that analysis into a short digital
signature: the fingerprint.

The same recording always produces the same (or very similar) fingerprint, even if:
- The file is in a different format (MP3 vs AAC vs FLAC)
- The bitrate is different (128kbps vs 320kbps)
- The file has been lightly edited (faded in, trimmed)

This is similar to a human fingerprint — unique to each recording, compact enough to
compare quickly against millions of others, and robust to small variations.

What it cannot survive: completely different recordings of the same song (a live version
will have a different fingerprint from the studio version), and heavily distorted or
corrupted audio.

---

## How Shazam identifies a song

The Shazam process, at a conceptual level:

1. Takes a short sample of audio — as little as 5–10 seconds is usually enough
2. Generates a fingerprint from the frequency patterns in that sample
3. Sends the fingerprint to a database of 200 million+ known song fingerprints
4. Compares the incoming fingerprint against stored fingerprints to find a close match
5. If a close match is found: returns the metadata — title, artist, album, year, cover art
6. If no match is found: returns nothing

**Why this works with garbled filenames:** Shazam does not read the filename. It listens
to the actual audio. A file called `track_882_FINAL_v2.mp3` that contains Vaseegara will
be identified as Vaseegara — because the audio fingerprint matches Vaseegara's entry in
Shazam's database.

**Why it sometimes fails:** The song's fingerprint was never submitted to Shazam's
database. This is common for very obscure recordings, very old regional music that was
never digitised and Shazamed by anyone, and locally-recorded or privately-distributed
music. Shazam's database grows because people use the Shazam app to identify songs — if
no one ever Shazamed a particular recording, it has no entry.

---

## How this pipeline uses ShazamIO

ShazamIO is a Python library that sends audio files to Shazam's recognition service
and returns the metadata as a Python dictionary. No API key is needed — it uses the
same internal endpoint the Shazam mobile app uses.

The pipeline sends each MP3 file through ShazamIO (Stage 1), receives the metadata,
stores it in the local SQLite database, and uses it to write ID3 tags (Stage 3) and
move the file to its final location (Stage 4). A 2-second sleep between Shazam calls
prevents rate limiting.

If ShazamIO returns no match, the file is marked `no_match` and held for manual review.
During `--review` mode, you can play the file, look up the song name however you like
(search the lyrics, ask someone who knows the music), and type the metadata in manually.
The pipeline uses your input exactly as if Shazam had returned it.

---

## What "manual review" means

When Shazam cannot identify a file, the pipeline marks it `no_match` and moves on to
the next file. Nothing is lost — the file is still in `Input/`, the database has a row
for it, and it is waiting.

During `--review` mode, you see each unmatched file one at a time. You can:
- Play the audio to hear what it is
- Skip it to come back later
- Enter the metadata by hand: `Title | Artist | Album | Year`

Once you enter metadata, the file proceeds through Stages 3 and 4 exactly as if Shazam
had identified it automatically. Your manual input (stored in `final_*` fields) always
takes priority over any Shazam data.

---

## Links

[README.md](../../README.md) | [User Guide](../guide/USER_GUIDE.md) | [Design Decisions](DESIGN_DECISIONS.md)
