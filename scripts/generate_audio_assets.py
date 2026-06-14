from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22_050


def _write(path: Path, duration: float, sample: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for index in range(int(duration * SAMPLE_RATE)):
        time = index / SAMPLE_RATE
        value = max(-1.0, min(1.0, sample(time, duration)))
        frames.extend(struct.pack("<h", int(value * 32767)))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def _tone(frequency: float, decay: float = 3.0, wobble: float = 0.0):
    def sample(time: float, duration: float) -> float:
        envelope = math.exp(-decay * time / duration)
        phase = 2.0 * math.pi * (frequency * time + wobble * math.sin(time * 8.0))
        return math.sin(phase) * envelope * 0.35

    return sample


def _noise(seed: int, frequency: float):
    randomizer = random.Random(seed)
    values = [randomizer.uniform(-1.0, 1.0) for _ in range(4096)]

    def sample(time: float, duration: float) -> float:
        envelope = math.sin(math.pi * time / duration) ** 2
        return values[int(time * frequency) % len(values)] * envelope * 0.24

    return sample


def _chord(frequencies: tuple[float, ...], pulse: float):
    def sample(time: float, duration: float) -> float:
        fade = math.sin(math.pi * time / duration) ** 2
        wave_value = sum(math.sin(2.0 * math.pi * frequency * time) for frequency in frequencies)
        return wave_value / len(frequencies) * fade * (0.22 + 0.05 * math.sin(time * pulse))

    return sample


def main() -> None:
    root = Path(__file__).parents[1] / "assets/audio"
    _write(root / "ui_click.wav", 0.08, _tone(880.0, 5.0))
    _write(root / "block_stone.wav", 0.18, _noise(11, 7000.0))
    _write(root / "block_earth.wav", 0.2, _noise(23, 1800.0))
    _write(root / "block_wood.wav", 0.16, _tone(170.0, 5.0, 0.2))
    _write(root / "footstep.wav", 0.12, _noise(37, 1200.0))
    _write(root / "mob_hit.wav", 0.2, _tone(120.0, 4.0, 0.5))
    _write(root / "mob_death.wav", 0.45, _tone(72.0, 2.0, 0.9))
    _write(root / "ambience_surface.wav", 4.0, _chord((55.0, 82.5, 110.0), 0.7))
    _write(root / "ambience_cave.wav", 4.0, _chord((41.2, 61.7, 92.5), 0.35))
    _write(root / "music_menu.wav", 6.0, _chord((110.0, 164.8, 220.0), 0.5))
    _write(root / "music_exploration.wav", 6.0, _chord((98.0, 146.8, 196.0), 0.8))
    _write(root / "music_night.wav", 6.0, _chord((73.4, 110.0, 146.8), 0.3))


if __name__ == "__main__":
    main()
