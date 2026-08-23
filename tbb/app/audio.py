"""CC0 audio facade with a quiet procedural fallback for no-device hosts."""
import math
import random
import struct
from pathlib import Path

import pygame

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio"


class AudioEngine:
    def __init__(self):
        self.ok = False
        self.sounds = {}
        self.ambient = None
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
            pygame.mixer.init(22050, -16, 1, 512)
        except Exception:
            return
        self.ok = True
        self._rand = random.Random(11)
        files = {"click": "ui_open.wav", "close": "ui_close.wav",
                 "hit": "melee_hit.wav", "death": "death_cry.wav",
                 "bow": "bow_shot.wav", "pain": "wound_cry.wav",
                 "hit_alt": "melee_hit_alt.wav",
                 "death_alt": "death_cry_alt.wav"}
        fallbacks = {"click": lambda: self._click(1000),
                     "close": lambda: self._click(700),
                     "hit": self._hit, "death": self._death}
        for name, filename in files.items():
            try:
                self.sounds[name] = pygame.mixer.Sound(str(ASSET_ROOT / filename))
            except Exception:
                try:
                    self.sounds[name] = pygame.mixer.Sound(buffer=fallbacks[name]())
                except Exception:
                    pass
        for name, buffer in (("bow", self._bow()), ("pain", self._pain()),
                             ("hit_alt", self._hit()),
                             ("death_alt", self._death()),
                             ("cant", self._click(180))):
            try:
                self.sounds[name] = pygame.mixer.Sound(buffer=buffer)
            except Exception:
                pass
        self.sounds["ui_open"] = self.sounds.get("click")
        self.sounds["ui_close"] = self.sounds.get("close")
        self.sounds["melee_hit"] = self.sounds.get("hit")
        self.sounds["death_cry"] = self.sounds.get("death")
        self.sounds["bow_shot"] = self.sounds.get("bow")
        self.sounds["wound_cry"] = self.sounds.get("pain")
        self.sounds["open"] = self.sounds.get("click")
        try:
            self.ambient = pygame.mixer.Sound(str(ASSET_ROOT / "ambient_loop.wav"))
        except Exception:
            try:
                self.ambient = pygame.mixer.Sound(buffer=self._ambient_loop())
            except Exception:
                self.ambient = None

    # ------------------------------------------------------------- gen
    def _pcm(self, samples):
        out = b""
        for v in samples:
            out += struct.pack("<h", max(-32768, min(32767, int(v))))
        return out

    def _click(self, freq=1000, ms=30):
        rate = 22050
        n = int(rate * ms / 1000)
        out = []
        for i in range(n):
            t = i / rate
            env = math.exp(-6 * t / (ms / 1000))
            v = math.sin(2 * math.pi * freq * t) * env * 0.5
            out.append(v * 32767)
        return self._pcm(out)

    def _hit(self):
        rate = 22050
        n = int(rate * 0.07)
        f0 = 230
        out = []
        for i in range(n):
            t = i / rate
            env = math.exp(-42 * t)
            v = math.sin(2 * math.pi * f0 * t) * env * 0.6
            v += (self._rand.random() - 0.5) * env * 0.55
            out.append(v * 32767)
        return self._pcm(out)

    def _bow(self):
        rate = 22050
        n = int(rate * 0.26)
        out = []
        for i in range(n):
            t = i / rate
            freq = 1500 - 600 * (t / 0.26)
            v = math.sin(2 * math.pi * freq * t) * math.exp(-9 * t) * 0.5
            out.append(v * 32767)
        return self._pcm(out)

    def _pain(self):
        rate = 22050
        n = int(rate * 0.5)
        out = []
        for i in range(n):
            t = i / rate
            a = math.sin(2 * math.pi * (196 - 50 * (t / 0.5)) * t)
            b = math.sin(2 * math.pi * (205 - 45 * (t / 0.5)) * t)
            v = (a + b) * math.exp(-3.2 * t) * 0.22
            out.append(v * 32767)
        return self._pcm(out)

    def _death(self):
        """A short descending death cry for the no-device fallback."""
        rate = 22050
        n = int(rate * 0.72)
        out = []
        for i in range(n):
            t = i / rate
            fall = 260 - 180 * (t / 0.72)
            voice = math.sin(2 * math.pi * fall * t)
            overtone = math.sin(2 * math.pi * fall * 1.51 * t) * 0.35
            out.append((voice + overtone) * math.exp(-2.8 * t) * 0.20 * 32767)
        return self._pcm(out)

    def _ambient_loop(self):
        rate = 22050
        dur = 4.0
        n = int(rate * dur)
        freqs = [55.0, 55.0 * 1.189, 55.0 * 1.498]
        out = []
        for i in range(n):
            t = i / rate
            w = 0.0
            for j, f in enumerate(freqs):
                w += math.sin(2 * math.pi * f * t +
                              math.sin(3 * t + j) * 0.3) * 0.11
            d = math.sin(2 * math.pi * 68 * t) * math.exp(-16 * (t % 2.0))
            br = (math.sin(2 * math.pi * 0.08 * t) * 0.5 + 0.5) * 0.07
            out.append((w + d + br) * 32767)
        return self._pcm(out)

    # ------------------------------------------------------------- play
    def sfx(self, name):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def music_start(self):
        if not self.ok or self.ambient is None:
            return
        try:
            self.ambient.play(loops=-1)
        except Exception:
            pass

    def music_stop(self):
        if not self.ok or self.ambient is None:
            return
        try:
            self.ambient.stop()
        except Exception:
            pass
