from __future__ import annotations

import math
import random
import struct
import wave
from collections.abc import Callable
from pathlib import Path

SAMPLE_RATE = 22_050
type Sample = Callable[[float, float], float]


def _write(path: Path, duration: float, sample: Sample, *, peak: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = [
        sample(index / SAMPLE_RATE, duration) for index in range(int(duration * SAMPLE_RATE))
    ]
    average = sum(samples) / max(len(samples), 1)
    centered = [value - average for value in samples]
    scale = peak / max(max((abs(value) for value in centered), default=1.0), 1e-6)
    frames = bytearray()
    for raw_value in centered:
        value = max(-1.0, min(1.0, raw_value * scale))
        frames.extend(struct.pack("<h", int(value * 32767)))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def _tone(frequency: float, decay: float = 3.0) -> Sample:
    def sample(time: float, duration: float) -> float:
        envelope = math.exp(-decay * time / duration)
        phase = 2.0 * math.pi * frequency * time
        return (math.sin(phase) + math.sin(phase * 2.01) * 0.22) * envelope

    return sample


def _noise(seed: int, frequency: float, decay: float = 1.0) -> Sample:
    randomizer = random.Random(seed)
    values = [randomizer.uniform(-1.0, 1.0) for _ in range(4096)]

    def sample(time: float, duration: float) -> float:
        attack = min(1.0, time / 0.008)
        envelope = attack * max(0.0, 1.0 - time / duration) ** decay
        index = int(time * frequency) % len(values)
        bright = values[index] - values[index - 1] * 0.58
        return bright * envelope

    return sample


def _chord(frequencies: tuple[float, ...], pulse: float) -> Sample:
    def sample(time: float, duration: float) -> float:
        fade = math.sin(math.pi * time / duration) ** 2
        wave_value = sum(math.sin(2.0 * math.pi * frequency * time) for frequency in frequencies)
        return wave_value / len(frequencies) * fade * (0.22 + 0.05 * math.sin(time * pulse))

    return sample


def _mix(*samples: tuple[Sample, float]) -> Sample:
    def sample(time: float, duration: float) -> float:
        return sum(generator(time, duration) * weight for generator, weight in samples)

    return sample


def _creature_voice(frequency: float, drop: float, rasp_seed: int) -> Sample:
    rasp = _noise(rasp_seed, 4200.0, 1.8)

    def sample(time: float, duration: float) -> float:
        progress = time / duration
        envelope = math.sin(math.pi * min(progress, 1.0)) ** 0.65
        phase = math.tau * (frequency * time + drop * time * time * 0.5)
        voice = math.sin(phase) * 0.72 + math.sin(phase * 2.02) * 0.20
        return envelope * voice + rasp(time, duration) * 0.18

    return sample


def main() -> None:
    root = Path(__file__).parents[1] / "assets/audio"
    _write(root / "ui_click.wav", 0.055, _tone(920.0, 8.0), peak=0.28)
    _write(root / "block_stone.wav", 0.14, _noise(11, 9200.0, 2.4), peak=0.54)
    _write(root / "block_earth.wav", 0.17, _noise(23, 2600.0, 1.7), peak=0.46)
    _write(
        root / "block_wood.wav",
        0.14,
        _mix((_tone(235.0, 7.0), 0.65), (_noise(31, 5200.0, 2.8), 0.35)),
        peak=0.48,
    )
    _write(root / "footstep.wav", 0.095, _noise(37, 3200.0, 2.2), peak=0.34)
    _write(root / "cow_hurt.wav", 0.34, _creature_voice(145.0, -35.0, 43), peak=0.42)
    _write(root / "cow_death.wav", 0.52, _creature_voice(125.0, -70.0, 47), peak=0.45)
    _write(root / "zombie_hurt.wav", 0.25, _creature_voice(185.0, -80.0, 53), peak=0.48)
    _write(root / "zombie_death.wav", 0.48, _creature_voice(150.0, -110.0, 59), peak=0.50)
    _write(root / "ambience_surface.wav", 4.0, _chord((110.0, 164.8, 220.0), 0.7), peak=0.16)
    _write(root / "ambience_cave.wav", 4.0, _chord((82.4, 123.5, 185.0), 0.35), peak=0.13)
    _write(root / "music_menu.wav", 6.0, _chord((146.8, 220.0, 293.7), 0.5), peak=0.18)
    _write(root / "music_exploration.wav", 6.0, _chord((130.8, 196.0, 261.6), 0.8), peak=0.16)
    _write(root / "music_night.wav", 6.0, _chord((110.0, 164.8, 220.0), 0.3), peak=0.15)


if __name__ == "__main__":
    main()
