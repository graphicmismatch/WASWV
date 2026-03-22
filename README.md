# WASWV

Woah Another Simple Waveform Viewer.

## What it does

Run:

```bash
./waswv <path_to_sound_file>
```

A desktop window opens and shows:

- the waveform for the sound file,
- extremely basic analysis tools and readouts,
- a button to open another file from inside the app.

## Current implementation

This initial implementation uses Python's built-in Tk GUI toolkit, so it works on macOS, Windows, and Linux anywhere Python with Tkinter is available.

The current build supports **WAV** input files and no longer relies on the deprecated `audioop` module.

## Features

- [x] CLI entry point: `waswv <path_to_sound_file>`
- [x] Native desktop window
- [x] Waveform drawing
- [x] Basic analysis: duration, sample rate, channels, frames, peak, RMS, zero crossings
- [x] Open another file from inside the app
- [x] No deprecated `audioop` dependency
- [x] `requirements.txt` included

## Run locally

```bash
python3 src/waswv.py path/to/file.wav
# or
./waswv path/to/file.wav
```

## Requirements

```bash
python3 -m pip install -r requirements.txt
```

The current `requirements.txt` is intentionally empty because the app only depends on Python's standard library.

## Packaging ideas

For shipping standalone binaries later, package the script with a platform-specific bundler such as:

- macOS: `py2app` or `PyInstaller`
- Windows: `PyInstaller`
- Linux: `PyInstaller` or a distro package
