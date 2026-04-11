"""
canvas.py
---------
Object-based drawing engine with multi-hand support and gesture hysteresis.
"""

import os
import cv2
import numpy as np

# --- Design Tokens ---
COLORS = {
    "Cyan": (255, 255, 0), "Azure": (255, 160, 0), "Violet": (255, 100, 200),
    "Magenta": (200, 50, 255), "Lime": (50, 255, 100), "Gold": (0, 200, 255),
    "White": (240, 240, 240)
}
NAMES = list(COLORS.keys())
SIZES = [4, 8, 14, 22]
BAR_H, SWATCH_W = 90, 70

# --- Aesthetic Settings ---
UI_DARK, UI_GLASS, UI_BORDER = (15, 15, 15), 0.5, (80, 80, 80)
NEON, GRAB = (255, 200, 0), (0, 100, 255)

class Stroke:
    """A collection of connected points with color/size metadata."""
    def __init__(self, color, size):
        self.color, self.size, self.points = color, size, []

    def add_point(self, pt):
        if not self.points or pt != self.points[-1]:
            self.points.append(pt)

    def draw(self, frame, is_selected=False):
        if not self.points: return
        if is_selected:
            pts = np.array(self.points, np.int32)
            cv2.polylines(frame, [pts], False, GRAB, self.size + 8, cv2.LINE_AA)
            
        if len(self.points) == 1:
            cv2.circle(frame, self.points[0], self.size // 2, self.color, -1, cv2.LINE_AA)
        else:
            for i in range(len(self.points) - 1):
                cv2.line(frame, self.points[i], self.points[i+1], self.color, self.size, cv2.LINE_AA)

    def move(self, dx, dy):
        self.points = [(x + dx, y + dy) for x, y in self.points]

    def is_near(self, pt, threshold=30):
        for p in self.points:
            if ((p[0]-pt[0])**2 + (p[1]-pt[1])**2)**0.5 < threshold: return True
        return False

class Canvas:
    """Unified interaction engine for multi-hand drawing and object manipulation."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        self._strokes = []
        self._active_ids = {} # hand_id -> current stroke
        self._grabbed = {}    # hand_id -> grabbed stroke
        self._prev_pp = {}    # hand_id -> last pinch pos
        self._smooth_pts = {} # hand_id -> smoothed landmark
        
        self._c_idx, self._s_idx = 0, 1
        self._eraser = False
        self._btn_lock = False
        self._pinching = set()
        self._pulses = {}

    def update(self, frame, hands):
        # 1. State Cleanup
        curr_ids = {h['id'] for h in hands}
        for hid in list(self._smooth_pts.keys()):
            if hid not in curr_ids:
                for d in [self._smooth_pts, self._active_ids, self._grabbed, self._prev_pp]:
                    if hid in d: del d[hid]

        if not any(h['tip_pos'][1] < BAR_H for h in hands): self._btn_lock = False

        # 2. Process Interaction
        for h in hands:
            hid = h['id']
            pt = self._ema(h['tip_pos'], self._smooth_pts.get(hid))
            self._smooth_pts[hid] = pt
            
            if pt[1] < BAR_H:
                self._handle_ui(pt)
                self._active_ids[hid] = self._grabbed[hid] = None
                if hid in self._pinching: self._pinching.remove(hid)
            else:
                # Pinch Hysteresis
                dist = h['norm_p_dist']
                if hid not in self._pinching and dist < 0.22:
                    self._pinching.add(hid)
                    self._pulses[hid] = 1.0
                elif hid in self._pinching and dist > 0.40:
                    self._pinching.remove(hid)
                
                self._handle_workspace(hid, pt, h['pinch_pos'], h['is_drawing'], hid in self._pinching)

        # 3. Rendering
        for s in self._strokes: s.draw(frame, s in self._grabbed.values())
        
        for h in hands:
            hid = h['id']
            pt = self._smooth_pts[hid]
            is_p = hid in self._pinching
            
            # Draw Cursors
            if is_p:
                color = GRAB
                cv2.drawMarker(frame, h['pinch_pos'], color, 1, 20, 2)
                cv2.circle(frame, h['pinch_pos'], 30, color, 1, cv2.LINE_AA)
                # Pulse Anim
                if self._pulses.get(hid, 0) > 0:
                    r = int(20 + 50 * (1.0 - self._pulses[hid]))
                    cv2.circle(frame, h['pinch_pos'], r, GRAB, 2, cv2.LINE_AA)
                    self._pulses[hid] -= 0.1
            else:
                color = self.color if h['is_drawing'] else NEON
                cv2.circle(frame, pt, SIZES[self._s_idx]//2 + 6, color, 1, cv2.LINE_AA)
                cv2.circle(frame, pt, 2, color, -1, cv2.LINE_AA)

        self._draw_toolbar(frame)
        return frame

    @property
    def color(self): return (0,0,0) if self._eraser else COLORS[NAMES[self._c_idx]]

    @property
    def brush_size(self): return SIZES[self._s_idx] * (3 if self._eraser else 1)

    def undo(self): 
        if self._strokes: self._strokes.pop()
        self._btn_lock = True

    def clear(self):
        self._strokes, self._btn_lock = [], True

    def save(self, name):
        out = "saved_canvas"
        if not os.path.exists(out): os.makedirs(out)
        path = os.path.join(out, name)
        snap = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        for s in self._strokes: s.draw(snap)
        cv2.imwrite(path, snap)

    def _ema(self, new, old):
        if not new: return None
        if not old: return new
        return (int(0.25 * new[0] + 0.75 * old[0]), int(0.25 * new[1] + 0.75 * old[1]))

    def _handle_workspace(self, hid, pt, pp, is_dw, is_p):
        if is_p and pp:
            if self._grabbed.get(hid):
                prev = self._prev_pp.get(hid)
                if prev: self._grabbed[hid].move(pp[0]-prev[0], pp[1]-prev[1])
                self._prev_pp[hid] = pp
            else:
                other_g = set(self._grabbed.values())
                for s in reversed(self._strokes):
                    if s not in other_g and s.is_near(pp):
                        self._grabbed[hid], self._prev_pp[hid] = s, pp
                        break
        else:
            self._grabbed[hid] = self._prev_pp[hid] = None
            if pt and is_dw:
                if self._eraser:
                    self._strokes = [s for s in self._strokes if not s.is_near(pt, self.brush_size * 1.5)]
                else:
                    if not self._active_ids.get(hid):
                        new_s = Stroke(self.color, self.brush_size)
                        self._strokes.append(new_s)
                        self._active_ids[hid] = new_s
                    self._active_ids[hid].add_point(pt)
            else: self._active_ids[hid] = None

    def _draw_toolbar(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, BAR_H), UI_DARK, -1)
        cv2.addWeighted(overlay, UI_GLASS, frame, 1 - UI_GLASS, 0, frame)
        cv2.line(frame, (0, BAR_H), (self.w, BAR_H), UI_BORDER, 1)

        for i, n in enumerate(NAMES):
            cx = i * SWATCH_W + SWATCH_W // 2
            if i == self._c_idx and not self._eraser: cv2.circle(frame, (cx, 35), 28, NEON, 2)
            cv2.circle(frame, (cx, 35), 22, COLORS[n], -1)
            cv2.putText(frame, n[:3].upper(), (i * SWATCH_W + 20, BAR_H - 12), 0, 0.35, (230,230,230), 1)

        tx = len(NAMES) * SWATCH_W + 20
        for i, lbl in enumerate(["UNDO", "ERASE", "CLEAR"]):
            x = tx + i * 85
            clr = (0, 150, 255) if (lbl == "ERASE" and self._eraser) else (40, 40, 40)
            cv2.rectangle(frame, (x, 20), (x + 75, BAR_H - 20), clr, -1)
            cv2.putText(frame, lbl, (x + 12, BAR_H // 2 + 5), 0, 0.4, (255,255,255), 1)

        sx = tx + 260
        for j, sz in enumerate(SIZES):
            scx = sx + j * 45
            if j == self._s_idx: cv2.circle(frame, (scx, BAR_H // 2), sz // 2 + 5, NEON, 1)
            cv2.circle(frame, (scx, BAR_H // 2), sz // 2 + 2, self.color, -1)

    def _handle_ui(self, pt):
        x, y = pt
        if x < len(NAMES) * SWATCH_W:
            self._c_idx, self._eraser = x // SWATCH_W, False
        if self._btn_lock: return

        tx = len(NAMES) * SWATCH_W + 20
        if tx < x < tx + 75: self.undo()
        elif tx + 85 < x < tx + 160: self._eraser, self._btn_lock = not self._eraser, True
        elif tx + 170 < x < tx + 250: self.clear()
        
        sx = tx + 260
        for j in range(len(SIZES)):
            if abs(x - (sx + j * 45)) < 20: self._s_idx = j
