"""
hand_tracker.py
---------------
Lightweight MediaPipe wrapper for high-speed multi-hand landmark tracking.
"""

import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np

# Joint Indices
T_TIP, I_TIP, I_PIP = 4, 8, 6
M_TIP, M_PIP, M_BASE = 12, 10, 9

# Full hand skeleton connections
SKELETON = [
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
    (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(0,17),
    (17,18),(18,19),(19,20)
]

class HandTracker:
    """Handles AI inference for hand landmarker detection."""
    def __init__(self, max_hands=2):
        model_path = os.path.join(os.path.dirname(__file__), "..", "assets", "models", "hand_landmarker.task")
        base = python.BaseOptions(model_asset_path=model_path)
        opts = vision.HandLandmarkerOptions(
            base_options=base,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=0.8,
            min_tracking_confidence=0.7,
        )
        self.client = vision.HandLandmarker.create_from_options(opts)
        self.results = None

    def process(self, frame, t_ms):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self.results = self.client.detect_for_video(img, t_ms)

    def get_hands_state(self, w, h):
        states = []
        if not self.results or not self.results.hand_landmarks: return states

        for i, lms in enumerate(self.results.hand_landmarks):
            # Scale calculation for depth normalization
            scale = ((lms[0].x - lms[M_BASE].x)**2 + (lms[0].y - lms[M_BASE].y)**2)**0.5
            scale = max(scale, 0.01)

            # Core Interaction Points
            it, tt = lms[I_TIP], lms[T_TIP]
            
            # Distance logic for Pinch (normalized)
            raw_d = ((tt.x-it.x)**2 + (tt.y-it.y)**2 + (tt.z-it.z)**2)**0.5
            norm_d = raw_d / scale
            
            states.append({
                'id': i,
                'tip_pos': (int(it.x * w), int(it.y * h)),
                'pinch_pos': (int((tt.x+it.x)/2 * w), int((tt.y+it.y)/2 * h)),
                'is_drawing': it.y < lms[I_PIP].y and not (lms[M_TIP].y < lms[M_PIP].y),
                'norm_p_dist': norm_d
            })
        return states

    def draw_landmarks(self, frame):
        if not self.results or not self.results.hand_landmarks: return
        h, w, _ = frame.shape
        for lms in self.results.hand_landmarks:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
            for conn in SKELETON:
                cv2.line(frame, pts[conn[0]], pts[conn[1]], (220, 220, 220), 1, cv2.LINE_AA)
            for pt in pts:
                cv2.circle(frame, pt, 2, (150, 255, 100), -1, cv2.LINE_AA)

    def close(self): self.client.close()
