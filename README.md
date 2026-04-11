# Air Canvas ✦

A high-performance virtual painting application powered by **MediaPipe Tasks** and **OpenCV**. Draw in thin air using hand gestures, manipulate individual objects, and collaborate with multiple users in real-time.

---

## ✨ Features

- **Object-Based Drawing**: Every stroke is an independent object. You can move, undo, or erase them individually.
- **Pinch-to-Move**: Pinch your thumb and index finger near a drawing to "grab" and reposition it anywhere on the canvas.
- **Multi-Hand Support**: Supports up to 2 hands simultaneously for collaborative creativity.
- **Glassmorphism UI**: A premium, translucent toolbar with tactile hand-tracking interaction.
- **High-Performance**: Multi-threaded architecture delivers smooth 60+ FPS video and responsive tracking.
- **Hand-Accessible Tools**: Toggle tools like **UNDO**, **ERASE**, and **CLEAR** by simply pointing at them.

---

## 🖐️ Gesture Guide

| Action | Physical Gesture | Description |
| :--- | :--- | :--- |
| **✏️ DRAW** | Index finger UP, Others DOWN | Paints with the currently selected color and size. |
| **🤏 MOVE** | **Pinch** (Thumb + Index touching) | Grab a drawing by pinching near it and drag to move. |
| **🧹 HOVER** | Index + Middle fingers UP | Move the cursor without drawing (for selecting tools). |
| **🧤 TOOLS** | Point at Toolbar | Hover over any button in the top bar to select colors/sizes or trigger Undo. |

---

## ⌨️ Keyboard Shortcuts

- **Q / Esc**: Quit the application immediately.
- **S**: Save the current drawing as a PNG image in the project root.
- **C**: Clear the entire canvas.
- **Z**: Undo the last stroke.

---

## 🛠️ Setup & Installation

1. **Prerequisites**:
   - Python 3.9 - 3.12 installed and added to PATH.
2. **Run the App**:
   - Simply double-click **`run_air_canvas.bat`**.
   - The script will automatically:
     - Create a virtual environment (`.venv`).
     - Install required dependencies (`mediapipe`, `opencv-python`, `numpy`).
     - Download the latest **MediaPipe Hand Landmarker** model.
     - Launch the application.

---

## 🏗️ Technical Details

- **Backend**: Python 3.12
- **Tracking**: MediaPipe Tasks API (Hand Landmarker)
- **Visualization**: OpenCV (High-GUI)
- **Architecture**: Multi-threaded Producer/Consumer for frame processing.

---

Enjoy your creative journey in thin air! 🚀
