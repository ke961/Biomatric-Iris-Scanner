# 👁️ Professional Biometric Iris Scanner Workstation

A real-time, jitter-free biometric iris scanning and eye telemetry workstation built with **Python** and **OpenCV**.

---

## ✨ Key Features

- **⚡ Ultra-Smooth Jitter Filtering**: Uses Adaptive Exponential Moving Average (EMA) with velocity damping and IoU tracking to eliminate box jumping and flickering.
- **🔔 Animated Alert Toast & Vignette System**: Dynamic slide-in glassmorphism notifications (`[SUCCESS]`, `[SECURITY ALERT]`, `[WARNING]`, `[SYSTEM]`) paired with pulsating screen border warning vignettes.
- **🔊 Multi-Tone Sound Effects**: Non-blocking acoustic synthesizer featuring rising harmonic chord melodies, danger sirens, camera shutter clicks, and target lock blips.
- **👁️ Liveness & Anti-Spoofing Blink Detection**: Counts natural physiological eye blinks in real-time to distinguish living eyes from printed photo spoofing attacks.
- **🗺️ Polar Iris Unwrap (Daugman Rubber Sheet PiP)**: Real-time polar unwrapping of the annular iris boundary into a linearized $(r, \theta)$ feature strip.
- **🎨 4 Multi-Spectral Color Themes**:
  - `CYBER BLUEPRINT` (Holographic Cyan / Emerald)
  - `TACTICAL NVG` (Military Night Vision Green)
  - `FLIR THERMAL IR` (False-color thermal heatmap)
  - `AMBER DEFENSE` (Sci-Fi Gold / Amber alert)
- **🗃️ Biometric Profile Database & Audit Logging**:
  - Enrolls biometric profiles into `biometric_db.json`.
  - Automatically logs every access attempt with confidence and liveness scores to `scan_audit_log.csv`.


---

## 🚀 How to Run

### 1. 📦 Installation & Dependencies
Ensure all dependencies are installed in your Python environment:
```bash
pip install -r requirements.txt
```

### 2. 🌐 Cyber Web Dashboard Workstation (Browser UI)
Launch the FastAPI-powered cyber telemetry web interface:
```bash
python web_app.py
```
> 🔗 Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser for the Cyber HUD telemetry suite, Web Audio acoustic synthesizer, ECG liveness pulse monitor, and access audit log.

### 3. 🖥️ Live OpenCV Desktop Workstation
Launch the native OpenCV desktop application with real-time camera tracking and Daugman polar unwrap PiP:
```bash
python scenner_iris.py
```

### 4. ✨ Biometric Simulation Demo (No Camera Needed)
Run the graphic animation simulation to test themes and UI elements without a webcam:
```bash
python demo_scenner_iris.py
```



---

## ⌨️ Controls & Shortcuts

| Key | Action |
|---|---|
| <kbd>SPACE</kbd> | Trigger Biometric Authentication Scan |
| <kbd>T</kbd> | Cycle Multi-Spectral Color Themes |
| <kbd>E</kbd> | Enroll Currently Locked Iris into Database |
| <kbd>M</kbd> | Toggle HUD Mode (Full Glassmorphism vs Minimal) |
| <kbd>C</kbd> | Capture and save biometric iris snapshot |
| <kbd>Q</kbd> / <kbd>ESC</kbd> | Exit application |

---

## 👤 Author
**Keya Khan**

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).

