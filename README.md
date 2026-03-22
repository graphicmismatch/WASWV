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
- [x] Automatically creates a virtual environment
- [x] Automatically installs dependencies from `requirements.txt`
- [x] Automatically reuses the same project virtual environment

## Run locally

```bash
./waswv path/to/file.wav
```

On the first run, the launcher will:

1. create `.venv` in the project root if it does not already exist,
2. install dependencies from `requirements.txt`, and
3. launch the app with that same environment.

If `requirements.txt` changes later, `./waswv` will detect the change and reinstall the dependencies into the same `.venv` automatically.

You can still run the app entry point directly if you already activated the environment yourself:

```bash
python3 src/waswv.py path/to/file.wav
```

## Requirements

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

The current `requirements.txt` is intentionally empty because the app only depends on Python's standard library, but the launcher still bootstraps and reuses the virtual environment so future dependencies can be added without changing how you start the app.

## Packaging ideas

For shipping standalone binaries later, package the script with a platform-specific bundler such as:

- macOS: `py2app` or `PyInstaller`
- Windows: `PyInstaller`
- Linux: `PyInstaller` or a distro package
