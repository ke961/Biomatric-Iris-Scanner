import cv2
import numpy as np
import time
import math
import hashlib
import json
import csv
import os
import io
import base64
import threading
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import scenner_iris
from scenner_iris import HUDTheme, BiometricHUD, SmoothBoxTracker, SmoothValue, BiometricDatabase, AlertNotificationManager

app = FastAPI(title="Biometric Iris Scanner Cyber Workstation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("snapshots", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/snapshots", StaticFiles(directory="snapshots"), name="snapshots")


# Theme Key Mappings between UI codes and internal themes
THEME_MAP = {
    "CYBER": "CYBER_CYAN",
    "CYBER_CYAN": "CYBER_CYAN",
    "NVG": "NIGHT_VISION",
    "NIGHT_VISION": "NIGHT_VISION",
    "THERMAL": "THERMAL_FLIR",
    "THERMAL_FLIR": "THERMAL_FLIR",
    "AMBER": "AMBER_RECON",
    "AMBER_RECON": "AMBER_RECON",
}

THEME_CODE_MAP = {
    "CYBER_CYAN": "CYBER",
    "NIGHT_VISION": "NVG",
    "THERMAL_FLIR": "THERMAL",
    "AMBER_RECON": "AMBER",
}


# ==============================================================================
#  STREAMING VIDEO & TELEMETRY ENGINE
# ==============================================================================

class WebIrisEngine:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

        self.tracker = SmoothBoxTracker(alpha=0.32, max_missed=10)
        self.hud = BiometricHUD()
        self.db = BiometricDatabase()
        self.alerts = AlertNotificationManager()
        self.fps_filter = SmoothValue(alpha=0.15)

        self.theme_keys = list(HUDTheme.THEMES.keys())
        self.current_theme_key = "CYBER_CYAN"

        self.scan_state = "IDLE"  # IDLE, SCANNING, VERIFIED, FAILED
        self.scan_start_time = 0
        self.scan_progress = 0.0
        self.authenticated_user = None
        self.hud_mode = "FULL"
        self.fps = 30.0
        self.last_polar_b64 = None
        self.last_bio_hash = "0x8F3A2B1C9D4E"
        self.active_targets = 0

        self.lock = threading.Lock()
        self.current_jpeg = None
        self.is_running = True
        self.has_camera = False

        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()

    @property
    def theme(self):
        canonical_key = THEME_MAP.get(self.current_theme_key, "CYBER_CYAN")
        return HUDTheme.THEMES.get(canonical_key, next(iter(HUDTheme.THEMES.values())))

    def set_theme(self, theme_key: str):
        canonical_key = THEME_MAP.get(theme_key)
        with self.lock:
            if canonical_key and canonical_key in HUDTheme.THEMES:
                self.current_theme_key = canonical_key
                self.alerts.post(f"THEME ACTIVATED: {self.theme['name']}", "INFO", duration=2.5)
                return True
            return False

    def trigger_scan(self):
        with self.lock:
            cur_time = time.time()
            if self.active_targets == 0 and self.has_camera:
                self.alerts.post("NO TARGET ACQUIRED // POSITION EYE IN FRAME", "WARNING", duration=3.0)
                return {"status": "warning", "message": "No active target in frame"}
            
            self.scan_state = "SCANNING"
            self.scan_start_time = cur_time
            self.scan_progress = 0.0
            self.alerts.post("INITIALIZING BIOMETRIC IRIS SCAN...", "INFO", duration=2.0)
            return {"status": "ok", "message": "Biometric scan initiated"}

    def capture_snapshot(self):
        with self.lock:
            filename = f"iris_capture_{int(time.time())}.jpg"
            filepath = os.path.join("snapshots", filename)
            if self.current_jpeg is not None:
                with open(filepath, "wb") as f:
                    f.write(self.current_jpeg)
                self.alerts.post(f"SNAPSHOT SAVED: {filename}", "INFO", duration=3.0, sound="shutter")
                return {"status": "ok", "filename": filename, "url": f"/snapshots/{filename}"}
            return {"status": "error", "message": "No frame available"}

    def _run_loop(self):
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            self.has_camera = True
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
        else:
            self.has_camera = False

        app_start_time = time.time()
        prev_time = time.time()

        while self.is_running:
            cur_time = time.time()
            dt = max(1e-5, cur_time - prev_time)
            fps = self.fps_filter.update(1.0 / dt)
            prev_time = cur_time
            elapsed = cur_time - app_start_time

            with self.lock:
                self.fps = fps
                theme = self.theme

            if self.has_camera and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    frame = self._generate_simulated_frame(elapsed, theme)
                else:
                    frame = cv2.flip(frame, 1)
            else:
                frame = self._generate_simulated_frame(elapsed, theme)

            h_img, w_img, _ = frame.shape

            # Theme filter effects
            if theme["apply_filter"] == "THERMAL":
                gray_raw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.applyColorMap(gray_raw, cv2.COLORMAP_INFERNO)
            elif theme["apply_filter"] == "NVG":
                gray_raw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.merge([np.zeros_like(gray_raw), gray_raw, np.zeros_like(gray_raw)])

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)

            # Detection
            detected_eyes = []
            if self.has_camera:
                faces = self.face_cascade.detectMultiScale(
                    enhanced_gray,
                    scaleFactor=1.18,
                    minNeighbors=5,
                    minSize=(110, 110)
                )

                if len(faces) > 0:
                    for (fx, fy, fw, fh) in faces:
                        eye_roi = enhanced_gray[fy:fy + int(fh * 0.55), fx:fx + fw]
                        eyes = self.eye_cascade.detectMultiScale(
                            eye_roi,
                            scaleFactor=1.08,
                            minNeighbors=5,
                            minSize=(28, 28),
                            maxSize=(int(fw * 0.42), int(fh * 0.42))
                        )
                        for (ex, ey, ew, eh) in eyes:
                            detected_eyes.append([fx + ex, fy + ey, ew, eh])
                else:
                    raw_eyes = self.eye_cascade.detectMultiScale(
                        enhanced_gray,
                        scaleFactor=1.15,
                        minNeighbors=6,
                        minSize=(35, 35)
                    )
                    detected_eyes = list(raw_eyes)
            else:
                # Simulation target eye coords
                cx, cy = w_img // 2, h_img // 2
                w_sim, h_sim = 140, 140
                detected_eyes = [[cx - w_sim // 2, cy - h_sim // 2, w_sim, h_sim]]

            tracks = self.tracker.update(detected_eyes, enhanced_gray)

            with self.lock:
                self.active_targets = sum(1 for t in tracks if t['missed'] <= 4)
                hash_seed = f"IRIS_{self.active_targets}_{int(elapsed * 2)}"
                self.last_bio_hash = "0x" + hashlib.md5(hash_seed.encode()).hexdigest()[:12].upper()

                # Update Polar Strip base64
                active_polar = next((t['iris_polar'] for t in tracks if t.get('iris_polar') is not None), None)
                if active_polar is not None:
                    try:
                        _, polar_buf = cv2.imencode('.png', active_polar)
                        self.last_polar_b64 = base64.b64encode(polar_buf).decode('utf-8')
                    except Exception:
                        pass

                # Scan state progression
                self._update_scan_state(cur_time, tracks, elapsed)

                # Render HUD
                if self.hud_mode == "FULL":
                    self._render_full_hud(frame, tracks, elapsed, fps, w_img, h_img, theme)
                else:
                    self._render_minimal_hud(frame, tracks, elapsed, fps, w_img, h_img, theme)

                self.alerts.draw(frame, w_img, h_img)

                # Encode to JPEG for web stream
                success, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if success:
                    self.current_jpeg = encoded_img.tobytes()

            time.sleep(0.025)

        if cap.isOpened():
            cap.release()

    def _generate_simulated_frame(self, elapsed, theme):
        w, h = 960, 540
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        cx, cy = w // 2, h // 2

        # Background Cyber Grid
        grid_color = (25, 35, 30)
        for gx in range(0, w, 40):
            cv2.line(frame, (gx, 0), (gx, h), grid_color, 1)
        for gy in range(0, h, 40):
            cv2.line(frame, (0, gy), (w, gy), grid_color, 1)

        # Rotating outer ring
        rot_angle = (elapsed * 45) % 360
        r_outer = 160
        cv2.circle(frame, (cx, cy), r_outer, theme["accent"], 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), r_outer - 12, (40, 70, 80), 1, cv2.LINE_AA)

        for a in range(0, 360, 15):
            rad = math.radians(a + rot_angle)
            p1 = (int(cx + (r_outer - 8) * math.cos(rad)), int(cy + (r_outer - 8) * math.sin(rad)))
            p2 = (int(cx + r_outer * math.cos(rad)), int(cy + r_outer * math.sin(rad)))
            cv2.line(frame, p1, p2, theme["accent"], 1, cv2.LINE_AA)

        # Counter-rotating iris texture lines
        for a in range(0, 360, 18):
            rad = math.radians(a - rot_angle * 1.6)
            p1 = (int(cx + 50 * math.cos(rad)), int(cy + 50 * math.sin(rad)))
            p2 = (int(cx + 120 * math.cos(rad)), int(cy + 120 * math.sin(rad)))
            cv2.line(frame, p1, p2, theme["secondary"], 1, cv2.LINE_AA)

        # Concentric pulsating circles
        pulse = math.sin(elapsed * 3) * 6
        cv2.circle(frame, (cx, cy), int(105 + pulse), theme["secondary"], 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), int(70 + pulse * 0.5), theme["accent"], 1, cv2.LINE_AA)

        # Pupil & Specular Reflection
        pupil_radius = int(38 + math.sin(elapsed * 2) * 4)
        cv2.circle(frame, (cx, cy), pupil_radius, (12, 14, 18), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), pupil_radius, theme["laser"], 2, cv2.LINE_AA)
        cv2.circle(frame, (cx - 10, cy - 10), 6, (255, 255, 255), -1, cv2.LINE_AA)

        # Vertical scanning laser beam
        laser_y = int(cy + math.sin(elapsed * 3.5) * (r_outer - 10))
        cv2.line(frame, (cx - r_outer, laser_y), (cx + r_outer, laser_y), theme["laser"], 2, cv2.LINE_AA)

        return frame

    def _update_scan_state(self, cur_time, tracks, elapsed):
        if self.scan_state == "SCANNING":
            duration = 2.2
            self.scan_progress = min(1.0, (cur_time - self.scan_start_time) / duration)
            if self.scan_progress >= 1.0:
                if len(tracks) > 0 or not self.has_camera:
                    self.scan_state = "VERIFIED"
                    first_profile = next(iter(self.db.profiles.values()), {
                        "name": "Abila Khan Keya (Admin)",
                        "clearance": "LEVEL 5 // ALPHA"
                    })
                    self.authenticated_user = first_profile
                    self.db.log_scan("IRIS-001", first_profile.get("name", "Abila Khan Keya"), "ACCESS_GRANTED", 99.4, 98.8)
                    self.alerts.post(f"IDENTITY VERIFIED: {first_profile.get('name')}", "SUCCESS", duration=4.0)
                else:
                    self.scan_state = "FAILED"
                    self.authenticated_user = None
                    self.db.log_scan("UNKNOWN", "Unidentified Subject", "ACCESS_DENIED", 32.1, 45.0)
                    self.alerts.post("SECURITY ALERT: ACCESS DENIED // IRIS MISMATCH", "DANGER", duration=4.0)
        elif self.scan_state in ("VERIFIED", "FAILED"):
            if cur_time - self.scan_start_time > 6.0:
                self.scan_state = "IDLE"
                self.authenticated_user = None

    def _render_full_hud(self, frame, tracks, elapsed, fps, w, h, theme):
        for track in tracks:
            if track['missed'] <= 5:
                self.hud.draw_reticle(frame, track, elapsed, theme)

        # 1. Top Status Bar
        self.hud.draw_glass_panel(frame, 15, 12, w - 30, 44, bg_color=theme["panel_bg"], alpha=0.75, border_color=theme["border"])
        cv2.putText(frame, f"BIOMETRIC IRIS WORKSTATION // [{theme['name']}]", (30, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.48, theme["accent"], 2, cv2.LINE_AA)

        sys_status = "READY" if self.scan_state == "IDLE" else self.scan_state
        status_color = theme["secondary"] if sys_status in ("READY", "VERIFIED") else theme["accent"]
        cv2.putText(frame, f"STATUS: {sys_status}", (w - 360, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.44, status_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 100, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.44, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 2. Bottom Authentication Banner
        bar_w, bar_h = 380, 14
        bx, by = (w - bar_w) // 2, h - 45
        self.hud.draw_glass_panel(frame, bx - 15, by - 20, bar_w + 30, 52, bg_color=theme["panel_bg"], alpha=0.75, border_color=theme["border"])

        if self.scan_state == "SCANNING":
            fill_w = int(bar_w * self.scan_progress)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), theme["accent"], -1)
            msg = f"AUTHENTICATING BIOMETRIC PATTERN... {int(self.scan_progress * 100)}%"
            cv2.putText(frame, msg, (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, theme["accent"], 1, cv2.LINE_AA)
        elif self.scan_state == "VERIFIED" and self.authenticated_user:
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), theme["secondary"], -1)
            user_text = f"ACCESS GRANTED // {self.authenticated_user['name']} ({self.authenticated_user['clearance']})"
            cv2.putText(frame, user_text, (bx - 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.36, theme["secondary"], 1, cv2.LINE_AA)
        elif self.scan_state == "FAILED":
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), self.hud.CRIMSON, -1)
            cv2.putText(frame, "ACCESS DENIED // IRIS MISMATCH OR SPOOF", (bx - 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.36, self.hud.CRIMSON, 1, cv2.LINE_AA)
        else:
            idle_prog = (math.sin(elapsed * 2.5) + 1.0) / 2.0
            fill_w = int(bar_w * idle_prog)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), (50, 90, 80), -1)
            cv2.putText(frame, "READY: [SPACE] SCAN | [T] THEME | [E] ENROLL", (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (80, 100, 110), 1, cv2.LINE_AA)

    def _render_minimal_hud(self, frame, tracks, elapsed, fps, w, h, theme):
        for track in tracks:
            if track['missed'] <= 4:
                self.hud.draw_reticle(frame, track, elapsed, theme)
        cv2.putText(frame, f"IRIS SCANNER // {theme['name']} [FPS: {fps:.1f}]", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.44, theme["accent"], 1, cv2.LINE_AA)


# Global Engine Instance
engine = WebIrisEngine()


# ==============================================================================
#  API MODELS & ROUTES
# ==============================================================================

class EnrollRequest(BaseModel):
    name: str
    clearance: str = "LEVEL 2 // OPERATOR"

class ThemeRequest(BaseModel):
    theme: str

def generate_video_stream():
    """Generator yielding multipart MJPEG frames for browser streaming."""
    while True:
        if engine.current_jpeg is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + engine.current_jpeg + b'\r\n')
        time.sleep(0.033)


@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = os.path.join("static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Biometric Iris Scanner Web Dashboard</h1>"


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/telemetry")
def get_telemetry():
    with engine.lock:
        theme_code = THEME_CODE_MAP.get(engine.current_theme_key, "CYBER")
        return {
            "fps": round(engine.fps, 1),
            "scan_state": engine.scan_state,
            "scan_progress": round(engine.scan_progress * 100, 1),
            "active_targets": engine.active_targets,
            "blinks": engine.tracker.total_blinks,
            "bio_hash": engine.last_bio_hash,
            "current_theme": theme_code,
            "theme_key": engine.current_theme_key,
            "theme_name": engine.theme["name"],
            "authenticated_user": engine.authenticated_user,
            "has_camera": engine.has_camera,
            "polar_map_b64": engine.last_polar_b64,
            "profiles_count": len(engine.db.profiles)
        }


@app.post("/api/scan")
def trigger_scan():
    return engine.trigger_scan()


@app.post("/api/theme")
def set_theme(req: ThemeRequest):
    ok = engine.set_theme(req.theme)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid theme name")
    theme_code = THEME_CODE_MAP.get(engine.current_theme_key, "CYBER")
    return {"status": "ok", "theme": theme_code, "name": engine.theme["name"]}


@app.get("/api/profiles")
def get_profiles():
    return engine.db.profiles


@app.post("/api/enroll")
def enroll_user(req: EnrollRequest):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    new_id = f"IRIS-{len(engine.db.profiles) + 1:03d}"
    seed = f"USER_{time.time()}_{req.name}"
    new_hash = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
    engine.db.enroll(new_id, req.name.strip(), req.clearance, new_hash)
    engine.alerts.post(f"BIOMETRIC ENROLLMENT // {req.name.strip()} ({new_id})", "SUCCESS", duration=3.5)
    return {"status": "ok", "id": new_id, "profile": engine.db.profiles[new_id]}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str):
    if profile_id in engine.db.profiles:
        del engine.db.profiles[profile_id]
        engine.db.save_db()
        return {"status": "ok", "message": f"Profile {profile_id} removed"}
    raise HTTPException(status_code=404, detail="Profile not found")


@app.get("/api/logs")
def get_audit_logs():
    logs = []
    log_file = "scan_audit_log.csv"
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    logs.append(row)
        except Exception:
            pass
    return list(reversed(logs[-50:]))


@app.post("/api/snapshot")
def take_snapshot():
    return engine.capture_snapshot()


@app.get("/api/snapshots")
def list_snapshots():
    if not os.path.exists("snapshots"):
        return []
    files = [f for f in os.listdir("snapshots") if f.endswith((".png", ".jpg"))]
    files.sort(reverse=True)
    return [{"filename": f, "url": f"/snapshots/{f}"} for f in files[:20]]


# ==============================================================================
#  ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 65)
    print("  👁️  BIOMETRIC IRIS SCANNER CYBER WEB WORKSTATION")
    print("  🚀  Running on: http://127.0.0.1:8000")
    print("=" * 65 + "\n")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
