"""Generate placeholder sound effects using the wave module."""

import os
import struct
import math

OUTPUT_DIR = "assets/sounds"


def generate_sine_wave(
    filename: str,
    frequency: float = 440.0,
    duration_ms: int = 100,
    sample_rate: int = 44100,
    amplitude: int = 32767,
):
    """Generate a simple sine wave .wav file."""
    num_samples = int(sample_rate * duration_ms / 1000)
    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wb") as f:
        # WAV header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + num_samples * 2))  # file size - 8
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # fmt chunk size
        f.write(struct.pack("<H", 1))   # PCM
        f.write(struct.pack("<H", 1))   # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))   # block align
        f.write(struct.pack("<H", 16))  # bits per sample
        f.write(b"data")
        f.write(struct.pack("<I", num_samples * 2))

        for i in range(num_samples):
            t = i / sample_rate
            value = int(amplitude * math.sin(2 * math.pi * frequency * t))
            f.write(struct.pack("<h", value))

    print(f"Generated: {filepath}")


if __name__ == "__main__":
    # UI click — short high-pitched blip
    generate_sine_wave("ui/click.wav", frequency=880, duration_ms=100)

    # UI confirm — slightly longer pleasant chime
    generate_sine_wave("ui/confirm.wav", frequency=660, duration_ms=200)

    print("Done.")
