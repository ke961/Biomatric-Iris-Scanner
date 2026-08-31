# 👁️ Professional Biometric Iris Scanner Workstation

A real-time, jitter-free biometric iris scanning and eye telemetry workstation built with **Python** and **OpenCV**.

---

## ✨ Key Features & Improvements

- **⚡ Ultra-Smooth Jitter Filtering**: Uses Adaptive Exponential Moving Average (EMA) with velocity damping and IoU tracking to eliminate box jumping and flickering.
- **🎯 Multi-Layer Holographic Reticle**:
  - Rotating outer azimuth ring with degree ticks.
  - Counter-rotating inner segmented arcs.
  - Corner tech brackets with dynamic lock score coloring (Amber ➔ Neon Green).
  - Pupil center crosshair and dark-core centroid localization.
  - Smooth sinusoidal scanning laser beam.
- **📊 Real-Time Biometric Telemetry**:
  - Live cryptographic biometric hash readout (`0x...`).
  - FPS counter with smooth frame-time estimation.
  - Target lock confidence score & liveness indicators.
  - Translucent glassmorphism panels with accented borders.
- **🎮 Interactive Authentication Simulation**:
  - Trigger live 3-second biometric pattern verification (`SPACE`).
  - Toggle between Full Holographic HUD and Minimalist mode (`M`).
  - Snapshot capture (`C`) saved directly to disk.

---

## 🚀 How to Run

### 1. Requirements
Ensure required libraries are installed:
```bash
pip install opencv-python numpy
```

### 2. Launching the Application
```bash
python scenner_iris.py
```

### 3. Running the Animation Demo (No Camera Needed)
```bash
python demo_scenner_iris.py
```

---

## ⌨️ Controls & Shortcuts

| Key | Action |
|---|---|
| <kbd>SPACE</kbd> | Trigger Biometric Authentication Scan |
| <kbd>M</kbd> | Toggle HUD Mode (Full Glassmorphism vs Minimal) |
| <kbd>C</kbd> | Capture and save biometric iris snapshot |
| <kbd>Q</kbd> / <kbd>ESC</kbd> | Exit application |

---

## 👤 Author
**Keya Khan**

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
