"""
main.py
-------
High-performance entry point for Air Canvas with multi-threaded hand tracking.
"""

import os
import ctypes
import time
import threading
import queue
import cv2
from ctypes import wintypes
from hand_tracker import HandTracker
from canvas import Canvas

def enable_high_dpi_awareness():
    """Ensures the application renders sharply on High DPI displays (Windows)."""
    if os.name != 'nt': return
    try:
        # 1. Windows 10 1703+: Per Monitor V2 (Best)
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except (AttributeError, OSError):
        try:
            # 2. Windows 8.1+: System DPI Aware
            # PROCESS_SYSTEM_DPI_AWARE = 1
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            try:
                # 3. Legacy Windows
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass

def get_dpi_scale():
    """Detects the current Windows DPI scale factor (e.g., 1.5 for 150%)."""
    if os.name != 'nt': return 1.0
    try:
        # GetDpiForSystem is the most reliable for initial window sizing
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except (AttributeError, OSError):
        return 1.0

# --- Global State ---
WINDOW_NAME = "Air Canvas"
CAM_WIDTH, CAM_HEIGHT = 1280, 720
SHOW_LANDMARKS = True
_ICON_HOLDER = []

class HandProcessor(threading.Thread):
    """Background worker for MediaPipe landmarker calls."""
    def __init__(self, tracker):
        super().__init__(daemon=True)
        self.tracker = tracker
        self.input_queue = queue.Queue(maxsize=1)
        self.running = True

    def run(self):
        while self.running:
            try:
                item = self.input_queue.get(timeout=0.05)
                if item is None: break
                frame, timestamp = item
                self.tracker.process(frame, timestamp)
                self.input_queue.task_done()
            except queue.Empty: continue

    def stop(self):
        self.running = False
        while not self.input_queue.empty():
            try: self.input_queue.get_nowait()
            except: break
        try: self.input_queue.put(None, timeout=0.1)
        except: pass

def set_window_icon():
    """Injects native Windows .ico into the running process and windows."""
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    png_path = os.path.join(assets_dir, "favicon.png")
    ico_path = os.path.join(assets_dir, "favicon.ico")
    
    # 1. Generate ICO from PNG if needed
    if os.path.exists(png_path) and not os.path.exists(ico_path):
        try:
            from PIL import Image
            img = Image.open(png_path)
            img.save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48), (256,256)])
        except: pass
        
    if not os.path.exists(ico_path): return

    # 2. Native Windows Injection (Title Bar Focus)
    try:
        hicon = ctypes.windll.user32.LoadImageW(None, ico_path, 1, 0, 0, 0x00000010)
        if not hicon: return
        _ICON_HOLDER.append(hicon) 

        # Direct injection into the Air Canvas window handle
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_NAME)
        if hwnd:
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon) # BIG
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon) # SMALL
    except: pass

def main():
    enable_high_dpi_awareness()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): return

    # Set and capture hardware resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    dpi_scale = get_dpi_scale()
    tracker = HandTracker(max_hands=2)
    canvas  = Canvas(w, h, dpi_scale=dpi_scale)
    processor = HandProcessor(tracker)
    processor.start()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    
    # Pulsed icon broadcast to ensure taskbar sync
    def icon_sync():
        for _ in range(10): 
            set_window_icon()
            time.sleep(0.5)
    threading.Thread(target=icon_sync, daemon=True).start()
    
    p_time = time.time()
    try:
        while True:
            # Exit check for window close
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1: break
            
            success, frame = cap.read()
            if not success: break
            frame = cv2.flip(frame, 1)
            t_ms = int(time.time() * 1000)

            try: processor.input_queue.put_nowait((frame.copy(), t_ms))
            except queue.Full: pass

            hands = tracker.get_hands_state(w, h)
            output = canvas.update(frame, hands)
            if SHOW_LANDMARKS: tracker.draw_landmarks(output)

            # Performance HUD
            fps = 1.0 / (time.time() - p_time + 1e-6)
            p_time = time.time()
            hud_w, hud_h = int(110 * dpi_scale), int(25 * dpi_scale)
            cv2.rectangle(output, (10, h - hud_h - 10), (10 + hud_w, h - 10), (15, 15, 15), -1)
            cv2.putText(output, f"{int(fps)} FPS", (20, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4 * dpi_scale, (200, 200, 200), max(1, int(1 * dpi_scale)), cv2.LINE_AA)

            cv2.imshow(WINDOW_NAME, output)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: break
            elif key == ord('c'): canvas.clear()
            elif key == ord('z'): canvas.undo()
            elif key == ord('s'): canvas.save(f"drawing_{int(time.time())}.png")
    finally:
        processor.stop()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        os._exit(0)

if __name__ == "__main__":
    main()
