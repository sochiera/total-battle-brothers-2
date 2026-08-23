#!/usr/bin/env python3
"""Generate the small original WAV cues shipped with the demo."""
import math
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parents[1] / "assets" / "audio"

def write(name, seconds, fn):
    frames = bytearray()
    for i in range(int(RATE * seconds)):
        value = fn(i / RATE, i / (RATE * seconds))
        frames.extend(struct.pack("<h", max(-32768, min(32767, int(value * 26000)))))
    with wave.open(str(OUT / name), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(RATE)
        stream.writeframes(frames)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write("bow_shot.wav", .24, lambda t, p: math.sin(2 * math.pi * (1500 - 600 * p) * t) * math.exp(-9 * t))
    write("wound_cry.wav", .5, lambda t, p: (math.sin(2 * math.pi * (196 - 50 * p) * t) + .5 * math.sin(2 * math.pi * 205 * t)) * math.exp(-3.2 * t))
    write("melee_hit_alt.wav", .09, lambda t, p: math.sin(2 * math.pi * 310 * t) * math.exp(-38 * t))
    write("death_cry_alt.wav", .7, lambda t, p: math.sin(2 * math.pi * (240 - 170 * p) * t) * math.exp(-2.8 * t))

if __name__ == "__main__":
    main()
