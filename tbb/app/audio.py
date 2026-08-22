"""Original procedural audio for Total Battle Brothers.

Sounds are synthesised in-memory (no copyrighted files): UI clicks, melee
thock, bow twang, a pain wail, and a long droning ambient campaign loop.
If the platform has no audio device the engine silently disables sound.
"""
import math
import random
import struct

import pygame


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
        try:
            self.sounds["click"] = pygame.mixer.Sound(buffer=self._click(1000))
            self.sounds["close"] = pygame.mixer.Sound(buffer=self._click(700))
            self.sounds["hit"] = pygame.mixer.Sound(buffer=self._hit())
            self.sounds["bow"] = pygame.mixer.Sound(buffer=self._bow())
            self.sounds["pain"] = pygame.mixer.Sound(buffer=self._pain())
            self.sounds["cant"] = pygame.mixer.Sound(buffer=self._click(180))
        except Exception:
            pass
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