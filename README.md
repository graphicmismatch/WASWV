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

This initial implementation is dependency-free and uses Python's built-in Tk GUI toolkit, so it works on macOS, Windows, and Linux anywhere Python with Tkinter is available.

The current build supports **WAV** input files so the project stays simple and portable without extra native dependencies.

## Features

- [x] CLI entry point: `waswv <path_to_sound_file>`
- [x] Native desktop window
- [x] Waveform drawing
- [x] Basic analysis: duration, sample rate, channels, frames, peak, RMS, zero crossings
- [x] Open another file from inside the app

## Run locally

```bash
python3 src/waswv.py path/to/file.wav
# or
./waswv path/to/file.wav
```

## Packaging ideas

For shipping standalone binaries later, package the script with a platform-specific bundler such as:

- macOS: `py2app` or `PyInstaller`
- Windows: `PyInstaller`
- Linux: `PyInstaller` or a distro package
