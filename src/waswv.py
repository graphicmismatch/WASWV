#!/usr/bin/env python3
from __future__ import annotations

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
WAVEFORM_PAD_X = 20
WAVEFORM_PAD_Y = 24
MIN_ZOOM = 1.0
MAX_ZOOM = 256.0
ZOOM_STEPS = 80


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
    samples: list[float]


def load_wave_file(path: Path) -> WaveformData:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only WAV files are supported in this dependency-free build.")

    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw_frames = wav_file.readframes(frame_count)

    channel_samples = decode_samples(raw_frames, sample_width)
    if not channel_samples:
        raise ValueError("No audio samples were found in the file.")

    samples = mix_to_mono(channel_samples, channels)
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    zero_crossings = sum(
        1
        for left, right in zip(samples, samples[1:])
        if (left >= 0 > right) or (left < 0 <= right)
    )

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
        samples=samples,
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


def mix_to_mono(samples: list[float], channels: int) -> list[float]:
    if channels <= 1:
        return samples

    mono_samples = []
    for index in range(0, len(samples), channels):
        frame = samples[index:index + channels]
        if frame:
            mono_samples.append(sum(frame) / len(frame))
    return mono_samples


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds - minutes * 60
    return f"{minutes:d}:{remaining_seconds:05.2f}"


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


class WaveformApp:
    def __init__(self, initial_path: Path | None) -> None:
        self.root = tk.Tk()
        self.root.title("WASWV - Woah Another Simple Waveform Viewer")
        self.root.geometry("1200x700")
        self.root.minsize(900, 600)
        self.data: WaveformData | None = None
        self.zoom = 1.0
        self.viewport_start = 0.0
        self._updating_zoom_scale = False

        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=10, pady=10)

        open_button = tk.Button(toolbar, text="Open audio file", command=self.open_file)
        open_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Open a WAV file to begin")
        status_label = tk.Label(toolbar, textvariable=self.status_var, anchor="w")
        status_label.pack(side=tk.LEFT, padx=12)

        zoom_controls = tk.Frame(toolbar)
        zoom_controls.pack(side=tk.RIGHT)

        tk.Button(zoom_controls, text="-", width=3, command=lambda: self.step_zoom(-1)).pack(side=tk.LEFT)
        self.zoom_scale = tk.Scale(
            zoom_controls,
            from_=0,
            to=ZOOM_STEPS,
            orient=tk.HORIZONTAL,
            length=180,
            resolution=1,
            showvalue=False,
            command=self.on_zoom_scale,
        )
        self.zoom_scale.pack(side=tk.LEFT, padx=6)
        tk.Button(zoom_controls, text="+", width=3, command=lambda: self.step_zoom(1)).pack(side=tk.LEFT)
        tk.Button(zoom_controls, text="Fit", command=self.reset_view).pack(side=tk.LEFT, padx=(6, 0))

        self.view_var = tk.StringVar(value="Zoom 1.0x")
        tk.Label(toolbar, textvariable=self.view_var, anchor="e", width=32).pack(side=tk.RIGHT, padx=(0, 12))

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
            text="Tips:\n• Use mouse wheel or +/- to zoom\n• Drag the scrollbar or use arrow keys to pan\n• Use Fit to return to the full waveform",
            justify=tk.LEFT,
            anchor="nw",
        )
        tips.grid(row=len(self.analysis_vars), column=0, columnspan=2, sticky="w", padx=8, pady=(16, 8))

        canvas_frame = tk.LabelFrame(self.root, text="Waveform")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(canvas_frame, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda event: self.on_linux_scroll(event, 1.25))
        self.canvas.bind("<Button-5>", lambda event: self.on_linux_scroll(event, 1 / 1.25))

        self.scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.on_scrollbar)
        self.scrollbar.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.root.bind("+", lambda _event: self.step_zoom(1))
        self.root.bind("=", lambda _event: self.step_zoom(1))
        self.root.bind("-", lambda _event: self.step_zoom(-1))
        self.root.bind("0", lambda _event: self.reset_view())
        self.root.bind("<Left>", lambda _event: self.pan_by_fraction(-0.15))
        self.root.bind("<Right>", lambda _event: self.pan_by_fraction(0.15))

        if initial_path is not None:
            self.load_path(initial_path)

        self.reset_view()

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
        self.reset_view()

    def visible_duration(self) -> float:
        if not self.data:
            return 1.0
        return max(self.data.duration_seconds / self.zoom, 0.001)

    def max_viewport_start(self, visible_duration: float | None = None) -> float:
        if not self.data:
            return 0.0
        if visible_duration is None:
            visible_duration = self.visible_duration()
        return max(self.data.duration_seconds - visible_duration, 0.0)

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.viewport_start = 0.0
        self.sync_zoom_scale()
        self.redraw()

    def slider_value_for_zoom(self, zoom: float) -> float:
        if MAX_ZOOM == MIN_ZOOM:
            return 0.0
        return round((math.log2(zoom) / math.log2(MAX_ZOOM)) * ZOOM_STEPS)

    def zoom_for_slider_value(self, slider_value: float) -> float:
        return 2 ** ((slider_value / ZOOM_STEPS) * math.log2(MAX_ZOOM))

    def sync_zoom_scale(self) -> None:
        self._updating_zoom_scale = True
        self.zoom_scale.set(self.slider_value_for_zoom(self.zoom))
        self._updating_zoom_scale = False

    def on_zoom_scale(self, raw_value: str) -> None:
        if self._updating_zoom_scale:
            return
        self.set_zoom(self.zoom_for_slider_value(float(raw_value)))

    def set_zoom(self, new_zoom: float, anchor_fraction: float = 0.5) -> None:
        if not self.data:
            self.zoom = clamp(new_zoom, MIN_ZOOM, MAX_ZOOM)
            self.sync_zoom_scale()
            self.redraw()
            return

        bounded_zoom = clamp(new_zoom, MIN_ZOOM, MAX_ZOOM)
        old_visible = self.visible_duration()
        anchor_fraction = clamp(anchor_fraction, 0.0, 1.0)
        anchor_time = self.viewport_start + old_visible * anchor_fraction
        self.zoom = bounded_zoom
        new_visible = self.visible_duration()
        self.viewport_start = clamp(
            anchor_time - new_visible * anchor_fraction,
            0.0,
            self.max_viewport_start(new_visible),
        )
        self.sync_zoom_scale()
        self.redraw()

    def zoom_at(self, factor: float, anchor_fraction: float) -> None:
        self.set_zoom(self.zoom * factor, anchor_fraction)

    def step_zoom(self, direction: int) -> None:
        factor = 1.25 if direction > 0 else 1 / 1.25
        self.zoom_at(factor, 0.5)

    def pan_by_fraction(self, direction: float) -> None:
        if not self.data:
            return
        visible = self.visible_duration()
        self.viewport_start = clamp(
            self.viewport_start + visible * direction,
            0.0,
            self.max_viewport_start(visible),
        )
        self.redraw()

    def on_scrollbar(self, *args: str) -> None:
        if not self.data:
            return

        visible = self.visible_duration()
        max_start = self.max_viewport_start(visible)
        if max_start <= 0:
            self.viewport_start = 0.0
            self.redraw()
            return

        if args[0] == "moveto":
            self.viewport_start = clamp(float(args[1]) * max_start, 0.0, max_start)
        elif args[0] == "scroll":
            step_count = int(args[1])
            step_size = visible * (0.1 if args[2] == "units" else 0.9)
            self.viewport_start = clamp(
                self.viewport_start + step_count * step_size,
                0.0,
                max_start,
            )
        self.redraw()

    def on_mouse_wheel(self, event: tk.Event[tk.Misc]) -> str:
        width = max(self.canvas.winfo_width(), 1)
        anchor_fraction = clamp(event.x / width, 0.0, 1.0)
        factor = 1.25 if event.delta > 0 else 1 / 1.25
        self.zoom_at(factor, anchor_fraction)
        return "break"

    def on_linux_scroll(self, event: tk.Event[tk.Misc], factor: float) -> str:
        width = max(self.canvas.winfo_width(), 1)
        anchor_fraction = clamp(event.x / width, 0.0, 1.0)
        self.zoom_at(factor, anchor_fraction)
        return "break"

    def update_view_summary(self) -> None:
        if not self.data:
            self.view_var.set(f"Zoom {self.zoom:.1f}x")
            return
        visible = self.visible_duration()
        start = self.viewport_start
        end = min(start + visible, self.data.duration_seconds)
        self.view_var.set(
            f"Zoom {self.zoom:.1f}x | {format_time(start)} - {format_time(end)}"
        )

    def update_scrollbar(self) -> None:
        if not self.data:
            self.scrollbar.set(0.0, 1.0)
            return

        duration = max(self.data.duration_seconds, 0.001)
        visible = min(self.visible_duration(), duration)
        start_fraction = clamp(self.viewport_start / duration, 0.0, 1.0)
        end_fraction = clamp((self.viewport_start + visible) / duration, 0.0, 1.0)
        self.scrollbar.set(start_fraction, end_fraction)

    def draw_empty_state(self, width: int, height: int) -> None:
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Open a WAV file to display its waveform",
            fill="#dddddd",
            font=("Arial", 18),
        )

    def draw_grid(self, width: int, height: int, middle_y: float) -> None:
        self.canvas.create_line(0, middle_y, width, middle_y, fill="#444444")
        inner_width = max(width - 2 * WAVEFORM_PAD_X, 1)
        for tick_index in range(5):
            x = WAVEFORM_PAD_X + (inner_width * tick_index / 4)
            self.canvas.create_line(x, WAVEFORM_PAD_Y, x, height - WAVEFORM_PAD_Y, fill="#1f1f1f")

    def build_envelope(
        self,
        samples: list[float],
        start_index: int,
        end_index: int,
        pixel_width: int,
    ) -> list[tuple[float, float]]:
        visible_sample_count = max(end_index - start_index, 1)
        buckets: list[tuple[float, float]] = []
        for pixel in range(pixel_width):
            bucket_start = start_index + (pixel * visible_sample_count) // pixel_width
            bucket_end = start_index + ((pixel + 1) * visible_sample_count) // pixel_width
            if bucket_end <= bucket_start:
                bucket_end = min(bucket_start + 1, end_index)
            chunk = samples[bucket_start:bucket_end]
            if not chunk:
                buckets.append((0.0, 0.0))
                continue
            buckets.append((min(chunk), max(chunk)))
        return buckets

    def draw_envelope(self, width: int, height: int, start_index: int, end_index: int) -> None:
        assert self.data is not None
        inner_width = max(width - 2 * WAVEFORM_PAD_X, 1)
        amplitude_scale = (height / 2) - WAVEFORM_PAD_Y
        middle_y = height / 2
        envelope = self.build_envelope(self.data.samples, start_index, end_index, inner_width)
        for pixel, (minimum, maximum) in enumerate(envelope):
            x = WAVEFORM_PAD_X + pixel
            y0 = middle_y - maximum * amplitude_scale
            y1 = middle_y - minimum * amplitude_scale
            self.canvas.create_line(x, y0, x, y1, fill="#64d2ff")

    def draw_samples(self, width: int, height: int, start_index: int, end_index: int) -> None:
        assert self.data is not None
        visible_samples = max(end_index - start_index, 1)
        amplitude_scale = (height / 2) - WAVEFORM_PAD_Y
        middle_y = height / 2
        inner_width = max(width - 2 * WAVEFORM_PAD_X, 1)
        x_scale = inner_width / max(visible_samples - 1, 1)
        scaled_points: list[float] = []
        for offset, sample_index in enumerate(range(start_index, end_index)):
            x = WAVEFORM_PAD_X + offset * x_scale
            y = middle_y - self.data.samples[sample_index] * amplitude_scale
            scaled_points.extend((x, y))
        if len(scaled_points) >= 4:
            self.canvas.create_line(*scaled_points, fill="#64d2ff", width=2, smooth=False)

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), CANVAS_WIDTH)
        height = max(self.canvas.winfo_height(), CANVAS_HEIGHT)
        middle_y = height / 2
        self.draw_grid(width, height, middle_y)
        self.update_view_summary()
        self.update_scrollbar()

        if not self.data or not self.data.samples:
            self.draw_empty_state(width, height)
            return

        visible = self.visible_duration()
        self.viewport_start = clamp(self.viewport_start, 0.0, self.max_viewport_start(visible))
        start_index = int(self.viewport_start * self.data.sample_rate)
        end_time = min(self.viewport_start + visible, self.data.duration_seconds)
        end_index = max(start_index + 1, int(math.ceil(end_time * self.data.sample_rate)))
        end_index = min(end_index, len(self.data.samples))
        visible_sample_count = max(end_index - start_index, 1)
        inner_width = max(width - 2 * WAVEFORM_PAD_X, 1)
        samples_per_pixel = visible_sample_count / inner_width

        if samples_per_pixel <= 4:
            self.draw_samples(width, height, start_index, end_index)
        else:
            self.draw_envelope(width, height, start_index, end_index)

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
