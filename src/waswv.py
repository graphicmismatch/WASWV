#!/usr/bin/env python3
from __future__ import annotations

import audioop
import math
import struct
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

SUPPORTED_EXTENSIONS = {".wav"}
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 360
MAX_POINTS = 2000


@dataclass
class WaveformData:
    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    frame_count: int
    duration_seconds: float
    peak: float
    rms: float
    zero_crossings: int
    waveform_points: list[tuple[float, float]]


def load_wave_file(path: Path) -> WaveformData:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only WAV files are supported in this dependency-free build.")

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw_frames = wav_file.readframes(frame_count)

    mono_frames = audioop.tomono(raw_frames, sample_width, 0.5, 0.5) if channels >= 2 else raw_frames
    samples = decode_samples(mono_frames, sample_width)
    if not samples:
        raise ValueError("No audio samples were found in the file.")

    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    zero_crossings = sum(
        1
        for left, right in zip(samples, samples[1:])
        if (left >= 0 > right) or (left < 0 <= right)
    )

    waveform_points = build_waveform_points(samples, sample_rate)

    return WaveformData(
        path=path,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
        frame_count=frame_count,
        duration_seconds=frame_count / sample_rate if sample_rate else 0.0,
        peak=peak,
        rms=rms,
        zero_crossings=zero_crossings,
        waveform_points=waveform_points,
    )


def decode_samples(raw_frames: bytes, sample_width: int) -> list[float]:
    if sample_width == 1:
        values = struct.unpack(f"<{len(raw_frames)}B", raw_frames)
        return [((value - 128) / 128.0) for value in values]
    if sample_width == 2:
        count = len(raw_frames) // 2
        values = struct.unpack(f"<{count}h", raw_frames)
        return [value / 32768.0 for value in values]
    if sample_width == 3:
        samples = []
        for index in range(0, len(raw_frames), 3):
            chunk = raw_frames[index:index + 3]
            int_value = int.from_bytes(chunk, byteorder="little", signed=False)
            if int_value & 0x800000:
                int_value -= 0x1000000
            samples.append(int_value / 8388608.0)
        return samples
    if sample_width == 4:
        count = len(raw_frames) // 4
        values = struct.unpack(f"<{count}i", raw_frames)
        return [value / 2147483648.0 for value in values]
    raise ValueError(f"Unsupported sample width: {sample_width} bytes")


def build_waveform_points(samples: list[float], sample_rate: int) -> list[tuple[float, float]]:
    chunk_size = max(1, len(samples) // MAX_POINTS)
    points = []
    for index in range(0, len(samples), chunk_size):
        chunk = samples[index:index + chunk_size]
        if not chunk:
            continue
        time_position = index / sample_rate if sample_rate else 0.0
        amplitude = sum(chunk) / len(chunk)
        points.append((time_position, amplitude))
    return points


class WaveformApp:
    def __init__(self, initial_path: Path | None) -> None:
        self.root = tk.Tk()
        self.root.title("WASWV - Woah Another Simple Waveform Viewer")
        self.root.geometry("1200x700")
        self.root.minsize(900, 600)
        self.data: WaveformData | None = None

        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=10, pady=10)

        open_button = tk.Button(toolbar, text="Open audio file", command=self.open_file)
        open_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Open a WAV file to begin")
        status_label = tk.Label(toolbar, textvariable=self.status_var, anchor="w")
        status_label.pack(side=tk.LEFT, padx=12)

        self.info_frame = tk.LabelFrame(self.root, text="Basic analysis")
        self.info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))

        self.analysis_vars = {
            "File": tk.StringVar(value="-"),
            "Duration": tk.StringVar(value="-"),
            "Sample rate": tk.StringVar(value="-"),
            "Channels": tk.StringVar(value="-"),
            "Frames": tk.StringVar(value="-"),
            "Peak": tk.StringVar(value="-"),
            "RMS": tk.StringVar(value="-"),
            "Zero crossings": tk.StringVar(value="-"),
        }
        for row, (label, variable) in enumerate(self.analysis_vars.items()):
            tk.Label(self.info_frame, text=label + ":", anchor="w", width=14).grid(row=row, column=0, sticky="w", padx=8, pady=6)
            tk.Label(self.info_frame, textvariable=variable, anchor="w", width=24).grid(row=row, column=1, sticky="w", padx=8, pady=6)

        tips = tk.Label(
            self.info_frame,
            text="Tips:\n• Use waswv <path_to_sound_file>\n• Drag the file picker to inspect another WAV\n• This zero-dependency build supports WAV input",
            justify=tk.LEFT,
            anchor="nw",
        )
        tips.grid(row=len(self.analysis_vars), column=0, columnspan=2, sticky="w", padx=8, pady=(16, 8))

        canvas_frame = tk.LabelFrame(self.root, text="Waveform")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(canvas_frame, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

        if initial_path is not None:
            self.load_path(initial_path)

    def open_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Open WAV file",
            filetypes=[("WAV audio", "*.wav")],
        )
        if filename:
            self.load_path(Path(filename))

    def load_path(self, path: Path) -> None:
        try:
            self.data = load_wave_file(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Unable to open file", str(exc))
            self.status_var.set(f"Failed to load {path}")
            return

        self.status_var.set(f"Loaded {path}")
        self.analysis_vars["File"].set(path.name)
        self.analysis_vars["Duration"].set(f"{self.data.duration_seconds:.2f} s")
        self.analysis_vars["Sample rate"].set(f"{self.data.sample_rate} Hz")
        self.analysis_vars["Channels"].set(str(self.data.channels))
        self.analysis_vars["Frames"].set(str(self.data.frame_count))
        self.analysis_vars["Peak"].set(f"{self.data.peak:.4f}")
        self.analysis_vars["RMS"].set(f"{self.data.rms:.4f}")
        self.analysis_vars["Zero crossings"].set(str(self.data.zero_crossings))
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), CANVAS_WIDTH)
        height = max(self.canvas.winfo_height(), CANVAS_HEIGHT)
        middle_y = height / 2
        self.canvas.create_line(0, middle_y, width, middle_y, fill="#444444")

        if not self.data or not self.data.waveform_points:
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="Open a WAV file to display its waveform",
                fill="#dddddd",
                font=("Arial", 18),
            )
            return

        duration = max(self.data.duration_seconds, 0.001)
        scaled_points: list[float] = []
        for time_position, amplitude in self.data.waveform_points:
            x = (time_position / duration) * (width - 40) + 20
            y = middle_y - amplitude * (height * 0.42)
            scaled_points.extend((x, y))

        if len(scaled_points) >= 4:
            self.canvas.create_line(*scaled_points, fill="#64d2ff", width=2, smooth=True)

    def run(self) -> None:
        self.redraw()
        self.root.mainloop()


def main() -> int:
    path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    app = WaveformApp(path)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
