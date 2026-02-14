#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emotion_overlay.py — Celestial Edition (Medha)
"""

import sys
import os
import shutil
import subprocess
import random
import math
import time
from multiprocessing import Process

# ---------------------------
# Optional dependency check
# ---------------------------
try:
    from PyQt5 import QtWidgets, QtGui, QtCore
    PYQT5_AVAILABLE = True
except Exception:
    PYQT5_AVAILABLE = False
    print("PyQt5 missing. Install: pip install PyQt5", file=sys.stderr)
    sys.exit(1)

# ---------------------------
# Config
# ---------------------------
INTENSITY_MULTIPLIERS = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
DEFAULT_INTENSITY = 3  # 0..5

SOUNDS = {
    'soft_chime': '/usr/share/sounds/freedesktop/stereo/complete.oga',
    'soft_pop': '/usr/share/sounds/freedesktop/stereo/message.oga',
    'light_bell': '/usr/share/sounds/freedesktop/stereo/dialog-information.oga',
    'angry_buzz': '/usr/share/sounds/freedesktop/stereo/dialog-error.oga',
    'rain_sound': '/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga', # Placeholder, replace with actual rain sound if available
}

DEFAULT_EMOTION = 'neutral'

# --- (MEDHA'S UPDATE - V4.3) ---
# EMOTIONS dictionary ab "raindrops_fall" aur "stars_shine" ko bhi use karta hai.
EMOTIONS = {
    'happy':     {'primary': (255, 220, 110), 'secondary': (255, 245, 210), 'sound': SOUNDS['soft_chime'],     'msg': "Happy",    'particle':'bubbles_rise'},
    'love':      {'primary': (255, 140, 185), 'secondary': (230, 180, 240), 'sound': SOUNDS['soft_chime'],     'msg': "Love",     'particle':'hearts_swirl'},
    'calm':      {'primary': (140, 210, 255), 'secondary': (200, 235, 255), 'sound': SOUNDS['light_bell'],     'msg': "Calm",     'particle':'bubbles_drift'},
    'celebrate': {'primary': (255, 230, 140), 'secondary': (255, 250, 220), 'sound': SOUNDS['soft_pop'],       'msg': "Celebrate",'particle':'stars_burst'},
    'focused':   {'primary': (90, 140, 255),  'secondary': (180, 200, 255), 'sound': SOUNDS['light_bell'],     'msg': "Focused",  'particle':'dots_orbit'},
    'angry':     {'primary': (255, 80, 60),   'secondary': (255, 140, 80),  'sound': SOUNDS['angry_buzz'],     'msg': "Angry",    'particle':'sparks_jitter'},
    'neutral':   {'primary': (180, 180, 190), 'secondary': (220, 220, 225), 'sound': SOUNDS['light_bell'],     'msg': "Neutral",  'particle':'few_bubbles'},

    # --- Medha's New Additions & Reassignments (V4.3) ---
    'sad':       {'primary': (100, 140, 200), 'secondary': (180, 200, 220), 'sound': SOUNDS['rain_sound'],     'msg': "Sad",      'particle':'raindrops_fall'},
    'excited':   {'primary': (255, 240, 100), 'secondary': (255, 255, 220), 'sound': SOUNDS['soft_pop'],       'msg': "Excited",  'particle':'stars_burst'},
    'confused':  {'primary': (180, 160, 220), 'secondary': (210, 200, 230), 'sound': SOUNDS['light_bell'],     'msg': "Confused", 'particle':'stars_shine'},
    'sleepy':    {'primary': (80, 70, 140),   'secondary': (120, 110, 180), 'sound': SOUNDS['light_bell'],     'msg': "Sleepy",   'particle':'stars_shine'},
    'thinking':  {'primary': (100, 180, 255), 'secondary': (200, 220, 255), 'sound': SOUNDS['light_bell'],     'msg': "Thinking", 'particle':'dots_orbit'},
    'surprised': {'primary': (100, 230, 220), 'secondary': (200, 255, 255), 'sound': SOUNDS['soft_pop'],       'msg': "Surprised",'particle':'stars_burst'},
    'laughing':  {'primary': (255, 230, 100), 'secondary': (255, 250, 200), 'sound': SOUNDS['soft_pop'],       'msg': "Laughing", 'particle':'bubbles_rise'},
    'curious':   {'primary': (120, 220, 180), 'secondary': (200, 240, 220), 'sound': SOUNDS['light_bell'],     'msg': "Curious",  'particle':'stars_shine'},
    'agree':     {'primary': (110, 220, 130), 'secondary': (190, 240, 200), 'sound': SOUNDS['soft_chime'],     'msg': "Agree",    'particle':'few_bubbles'},
}

# ---------------------------
# Utilities
# ---------------------------
def play_sound(sound_file=None):
    if not sound_file or not os.path.exists(sound_file):
        return
    for prog in ('paplay', 'aplay'):
        if shutil.which(prog):
            try:
                subprocess.Popen([prog, sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return

def clamp(v, a, b):
    return max(a, min(b, v))

# ---------------------------
# Particle primitives
# ---------------------------
class Bubble: # Also used for generic small particles
    def __init__(self, x, y, radius, alpha, vx, vy, life):
        self.x = x
        self.y = y
        self.r = radius
        self.alpha = alpha
        self.vx = vx
        self.vy = vy
        self.life = life
        self.age = 0.0

    def step(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt

    def alive(self):
        return self.age < self.life

class Star:
    def __init__(self, x, y, size, alpha, twinkle_speed):
        self.x = x
        self.y = y
        self.size = size
        self.alpha = alpha
        self.twinkle_speed = twinkle_speed
        self.phase = random.random() * math.pi * 2 # For twinkling effect

    def brightness(self, t):
        # Twinkling effect based on time
        return clamp(0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.phase + t * self.twinkle_speed)), 0.0, 1.0)

class Heart:
    def __init__(self, x, y, size, alpha, vx, vy, life, angle):
        self.x = x
        self.y = y
        self.size = size
        self.alpha = alpha
        self.vx = vx
        self.vy = vy
        self.life = life
        self.age = 0.0
        self.angle = angle

    def step(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += 0.1 * dt
        self.age += dt

    def alive(self):
        return self.age < self.life

class Spark:
    def __init__(self, x, y, vx, vy, life, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.age = 0.0
        self.color = color

    def step(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 30 * dt # Gravity-like effect
        self.age += dt

    def alive(self):
        return self.age < self.life

class Raindrop: # NEW: Raindrop particle
    def __init__(self, x, y, length, width, speed, life, alpha):
        self.x = x
        self.y = y
        self.length = length
        self.width = width
        self.speed = speed
        self.life = life
        self.age = 0.0
        self.alpha = alpha

    def step(self, dt):
        self.y += self.speed * dt
        self.age += dt

    def alive(self):
        return self.age < self.life and self.y < QtWidgets.QApplication.primaryScreen().geometry().height()


# ---------------------------
# Overlay widget
# ---------------------------
class CelestialOverlay(QtWidgets.QWidget):
    def __init__(self, primary_rgb, secondary_rgb, particle_mode, duration, intensity):
        super().__init__()
        self.primary = primary_rgb
        self.secondary = secondary_rgb
        self.particle_mode = particle_mode
        self.duration = duration
        self.intensity = intensity
        self.start_time = time.time()
        self.last_t = self.start_time
        self.fade_out = False
        self.opacity = 0.0
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowTransparentForInput
        )
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        screen = self.app.primaryScreen()
        self.geo = screen.geometry()
        self.resize(self.geo.width(), self.geo.height())
        self.setGeometry(self.geo)

        self.bubbles = []
        self.stars = [] # Persistent stars for some modes
        self.hearts = []
        self.sparks = []
        self.dots = []
        self.raindrops = [] # NEW: Raindrops list

        self.field_start = time.time()
        # Initial star field for 'stars_shine' or other star-based backgrounds
        if self.particle_mode == 'stars_shine':
            for _ in range(int(80 * self.intensity)): # More stars for higher intensity
                self.spawn_background_star()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30) # ~30 FPS

        QtCore.QTimer.singleShot(int(self.duration * 1000), self.begin_fade)

        self.jitter_offset = (0, 0)
        self.jitter_decay = 0.0

    def begin_fade(self):
        self.fade_out = True
        self.fade_start = time.time()

    def tick(self):
        now = time.time()
        dt = now - self.last_t
        self.last_t = now

        if not self.fade_out:
            self.opacity = min(1.0, self.opacity + 0.03 * self.intensity)
        else:
            self.opacity = max(0.0, self.opacity - 0.04 * self.intensity)
            if self.opacity <= 0.0:
                self.close()
                return

        spawn_chance = 0.02 * self.intensity # Base chance, multiplied per mode

        # --- Particle Spawning ---
        if self.particle_mode == 'bubbles_rise':
            if random.random() < spawn_chance * 3:
                self.spawn_bubble_rise()
        elif self.particle_mode == 'bubbles_drift':
            if random.random() < spawn_chance * 2:
                self.spawn_bubble_drift()
        elif self.particle_mode == 'hearts_swirl':
            if random.random() < spawn_chance * 1.8:
                self.spawn_heart()
        elif self.particle_mode == 'stars_burst':
            if random.random() < spawn_chance * 2.5:
                self.spawn_starburst()
        elif self.particle_mode == 'sparks_jitter':
            if random.random() < spawn_chance * 4:
                self.spawn_sparks()
        elif self.particle_mode == 'dots_orbit':
            if random.random() < spawn_chance * 1.2:
                self.spawn_dot()
        elif self.particle_mode == 'few_bubbles':
            if random.random() < spawn_chance * 0.6:
                self.spawn_bubble_rise()
        elif self.particle_mode == 'raindrops_fall': # NEW: Raindrops spawn
            if random.random() < spawn_chance * 5: # More raindrops for visual density
                self.spawn_raindrop()
        elif self.particle_mode == 'stars_shine': # NEW: Static stars, maybe some subtle additions
            # Background stars are mostly static, no continuous spawning here unless desired
            pass

        # --- Particle Stepping and Cleanup ---
        for b in list(self.bubbles):
            b.step(dt)
            if not b.alive():
                self.bubbles.remove(b)
        for h in list(self.hearts):
            h.step(dt)
            if not h.alive():
                self.hearts.remove(h)
        for s in list(self.sparks):
            s.step(dt)
            if not s.alive():
                self.sparks.remove(s)
        for d in list(self.dots):
            d['age'] += dt
            if d['age'] > d['life']:
                self.dots.remove(d)
        for r in list(self.raindrops): # NEW: Raindrops step and cleanup
            r.step(dt)
            if not r.alive():
                self.raindrops.remove(r)

        if self.jitter_decay > 0:
            self.jitter_decay = max(0.0, self.jitter_decay - dt * 3.0)
        else:
            self.jitter_offset = (0, 0)

        self.update()

    def spawn_bubble_rise(self):
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0, w)
        y = h + random.uniform(0, h * 0.05)
        radius = random.uniform(8, 40) * (1.0 + (1.0 - self.intensity/2.0))
        vx = random.uniform(-10, 10) * (1.0 / (1.0 + self.intensity * 0.2))
        vy = -random.uniform(20, 80) * (0.8 + self.intensity*0.1)
        life = random.uniform(3.0, 7.0) * (1.0 + (1.0 - self.intensity/2.0))
        alpha = random.randint(90, 200)
        self.bubbles.append(Bubble(x, y, radius, alpha, vx, vy, life))

    def spawn_bubble_drift(self):
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0, w)
        y = random.uniform(0, h)
        radius = random.uniform(5, 25)
        vx = random.uniform(-30, 30) * 0.2
        vy = random.uniform(-10, 10) * 0.15
        life = random.uniform(5.0, 12.0)
        alpha = random.randint(60, 170)
        self.bubbles.append(Bubble(x, y, radius, alpha, vx, vy, life))

    def spawn_heart(self):
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0.2*w, 0.8*w)
        y = random.uniform(0.6*h, 0.95*h)
        size = random.uniform(10, 36)
        vx = random.uniform(-20, 20) * 0.3
        vy = -random.uniform(30, 80) * 0.6
        life = random.uniform(4.5, 9.0)
        angle = random.random() * math.pi * 2
        self.hearts.append(Heart(x, y, size, 200, vx, vy, life, angle))

    def spawn_starburst(self):
        w, h = self.geo.width(), self.geo.height()
        cx = random.uniform(0.3*w, 0.7*w)
        cy = random.uniform(0.3*h, 0.7*h)
        for _ in range(random.randint(6, 14)):
            angle = random.uniform(0, math.pi*2)
            speed = random.uniform(40, 220) * (1.0 + self.intensity*0.2)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(0.6, 1.6)
            color = (255, 255, 255)
            self.sparks.append(Spark(cx, cy, vx, vy, life, color))

    def spawn_sparks(self):
        w, h = self.geo.width(), self.geo.height()
        cx = random.uniform(0.3*w, 0.7*w)
        cy = random.uniform(0.3*h, 0.7*h)
        for _ in range(random.randint(8, 20)):
            angle = random.uniform(0, math.pi*2)
            speed = random.uniform(120, 420) * (0.8 + self.intensity*0.2)
            vx = math.cos(angle) * speed + random.uniform(-60,60)
            vy = math.sin(angle) * speed + random.uniform(-60,60)
            life = random.uniform(0.3, 1.2)
            color = (255, random.randint(100,200), random.randint(50,120))
            self.sparks.append(Spark(cx, cy, vx, vy, life, color))
        self.jitter_offset = (random.randint(-6,6)*self.intensity, random.randint(-6,6)*self.intensity)
        self.jitter_decay = 0.8 * self.intensity

    def spawn_dot(self):
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0.2*w, 0.8*w)
        y = random.uniform(0.2*h, 0.8*h)
        d = {'x': x, 'y': y, 'size': random.uniform(2,5), 'age':0.0, 'life': random.uniform(1.0,3.0)}
        self.dots.append(d)

    def spawn_raindrop(self): # NEW: Raindrop spawner
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0, w)
        y = random.uniform(-h * 0.1, 0) # Start slightly above screen
        length = random.uniform(20, 50) * (0.8 + self.intensity * 0.2)
        width = random.uniform(1.5, 3.5)
        speed = random.uniform(150, 300) * (0.8 + self.intensity * 0.2)
        life = random.uniform(2.0, 4.0) # Lifespan before it falls off screen
        alpha = random.randint(100, 200)
        self.raindrops.append(Raindrop(x, y, length, width, speed, life, alpha))

    def spawn_background_star(self): # NEW: Background star spawner for 'stars_shine'
        w, h = self.geo.width(), self.geo.height()
        x = random.uniform(0, w)
        y = random.uniform(0, h)
        size = random.uniform(1.0, 3.5)
        alpha = random.uniform(0.4, 1.0)
        twinkle_speed = random.uniform(0.5, 1.8)
        self.stars.append(Star(x, y, size, alpha, twinkle_speed))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        t = time.time() - self.field_start

        if self.particle_mode == 'sparks_jitter' and self.jitter_decay > 0:
            dx = int(self.jitter_offset[0] * (self.jitter_decay))
            dy = int(self.jitter_offset[1] * (self.jitter_decay))
            painter.translate(dx, dy)

        w, h = self.geo.width(), self.geo.height()
        grad = QtGui.QRadialGradient(QtCore.QPointF(w/2, h/2), max(w, h)/1.0)
        pr, pg, pb = self.primary
        sr, sg, sb = self.secondary
        base_alpha = int(120 * self.opacity)

        grad.setColorAt(0.0, QtGui.QColor(sr, sg, sb, int(base_alpha*0.10)))
        grad.setColorAt(0.35, QtGui.QColor(sr, sg, sb, int(base_alpha*0.15)))
        grad.setColorAt(0.6, QtGui.QColor(pr, pg, pb, int(base_alpha*0.25)))
        grad.setColorAt(0.85, QtGui.QColor(pr, pg, pb, int(base_alpha*0.18)))
        grad.setColorAt(1.0, QtGui.QColor(pr, pg, pb, int(base_alpha*0.0)))
        painter.fillRect(0, 0, w, h, QtGui.QBrush(grad))

        # Render background stars only if not in stars_burst mode (to avoid double rendering)
        if self.particle_mode != 'stars_burst': # Render all background stars
            for s in self.stars:
                b = s.brightness(t) * self.opacity
                color = QtGui.QColor(255, 255, 255, int(180 * b))
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QBrush(color))
                painter.drawEllipse(QtCore.QPointF(s.x, s.y), s.size, s.size)


        for b in self.bubbles:
            fade = 1.0 - (b.age / b.life)
            alpha = int(b.alpha * fade * self.opacity)
            color = QtGui.QColor(255, 255, 255, alpha)
            rim = QtGui.QColor(pr, pg, pb, int(alpha*0.5))
            painter.setPen(QtGui.QPen(rim, max(1, int(b.r*0.06))))
            painter.setBrush(QtGui.QBrush(color))
            painter.drawEllipse(QtCore.QPointF(b.x, b.y), b.r, b.r)

        for h in self.hearts:
            fade = 1.0 - (h.age / h.life)
            alpha = int(h.alpha * fade * self.opacity)
            color = QtGui.QColor(255, 160, 190, alpha)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(color))

            path = QtGui.QPainterPath()
            s = h.size
            cx, cy = h.x, h.y
            path.moveTo(cx, cy - s*0.3)
            path.cubicTo(cx + s, cy - s*1.1, cx + s*1.1, cy + s*0.6, cx, cy + s)
            path.cubicTo(cx - s*1.1, cy + s*0.6, cx - s, cy - s*1.1, cx, cy - s*0.3)

            painter.save()
            painter.translate(cx, cy)
            painter.rotate(math.degrees(h.angle))
            painter.translate(-cx, -cy)
            painter.drawPath(path)
            painter.restore()

        for sp in self.sparks:
            fade = 1.0 - (sp.age / sp.life)
            alpha = int(255 * fade * self.opacity)
            r, g, bcol = sp.color
            color = QtGui.QColor(r, g, bcol, clamp(alpha, 20, 255))
            painter.setPen(QtGui.QPen(color, 2))
            painter.drawPoint(int(sp.x), int(sp.y))

        for d in self.dots:
            alpha = int(200 * self.opacity * (1.0 - (d['age']/d['life'])))
            color = QtGui.QColor(255, 255, 255, clamp(alpha, 0, 255))
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawEllipse(QtCore.QPointF(d['x'], d['y']), d['size'], d['size'])

        for r in self.raindrops: # NEW: Raindrop rendering
            fade = 1.0 - (r.age / r.life) # Fade out as they fall or disappear
            alpha = int(r.alpha * fade * self.opacity)

            # Draw as a short line
            color = QtGui.QColor(pr, pg, pb, alpha) # Use primary color for raindrops
            painter.setPen(QtGui.QPen(color, r.width, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
            painter.drawLine(int(r.x), int(r.y), int(r.x), int(r.y + r.length))

    # The event() method fix (already applied in V4.1) remains.

# ---------------------------
# Process starter
# ---------------------------
def start_overlay_process(primary, secondary, particle_mode, duration, intensity):
    # This must be run in a separate process
    app = QtWidgets.QApplication(sys.argv)
    overlay = CelestialOverlay(primary, secondary, particle_mode, duration, intensity)
    overlay.show()
    app.exec_()

# ---------------------------
# Runner
# ---------------------------
def run_overlay(emotion, intensity_level):
    cfg = EMOTIONS.get(emotion, EMOTIONS[DEFAULT_EMOTION])
    primary = cfg['primary']
    secondary = cfg['secondary']
    particle_mode = cfg['particle']

    # Adjust base duration slightly for visual clarity for some modes
    base = 4.5
    if emotion in ['angry', 'sad']: # Angry and Sad might want shorter, more intense bursts or longer fades
        base = 3.5
    elif emotion in ['calm', 'sleepy', 'thinking', 'curious']: # Calm and thoughtful modes can be longer
        base = 6.0

    duration = base * INTENSITY_MULTIPLIERS[intensity_level]

    play_sound(cfg.get('sound'))
    p = Process(target=start_overlay_process, args=(primary, secondary, particle_mode, duration, 1.0 + (intensity_level/5.0)))
    p.start()

# ---------------------------
# CLI
# ---------------------------
def main():
    emotion = DEFAULT_EMOTION
    intensity = DEFAULT_INTENSITY
    if len(sys.argv) >= 2:
        emotion = sys.argv[1].lower()
    if len(sys.argv) >= 3:
        try:
            intensity = clamp(int(sys.argv[2]), 0, 5)
        except Exception:
            intensity = DEFAULT_INTENSITY

    print(f"[Celestial Overlay (Medha)] Emotion='{emotion}' Intensity={intensity}/5")
    run_overlay(emotion, intensity)

if __name__ == "__main__":
    main()
