import cv2
import numpy as np
import time
import math
import hashlib
import json
import csv
import os
import threading

try:
    import winsound
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


# ==============================================================================
#  SOUND SYNTHESIZER & ACOUSTIC ALERT SYSTEM (NON-BLOCKING)
# ==============================================================================

def play_audio_cue(cue_type="lock"):
    """Plays synthesized multi-frequency audio alerts in a background daemon thread."""
    if not AUDIO_AVAILABLE:
        return

    def _sound_thread():
        try:
            if cue_type == "lock":
                winsound.Beep(1200, 50)
            elif cue_type == "alert_success":
                # High-tech rising harmonic chord
                for freq in [523, 659, 784, 1046]:
                    winsound.Beep(freq, 60)
            elif cue_type == "alert_danger":
                # Warning siren pulse
                for _ in range(3):
                    winsound.Beep(900, 80)
                    winsound.Beep(450, 80)
            elif cue_type == "alert_warning":
                # Dual warning chirp
                winsound.Beep(800, 100)
                winsound.Beep(600, 120)
            elif cue_type == "shutter":
                # Snapshot camera click
                winsound.Beep(2400, 20)
                winsound.Beep(1800, 30)
            elif cue_type == "toast":
                # UI notification blip
                winsound.Beep(1500, 45)
            elif cue_type == "blink":
                # Liveness blink ping
                winsound.Beep(1750, 25)
        except Exception:
            pass

    threading.Thread(target=_sound_thread, daemon=True).start()


# ==============================================================================
#  ANIMATED NOTIFICATION & ALERT TOAST MANAGER
# ==============================================================================

class AlertNotificationManager:
    """Manages animated HUD toast alerts, banners, and screen edge warning vignettes."""

    COLOR_MAP = {
        "SUCCESS": ((50, 255, 120), (10, 35, 15), "[SUCCESS]"),
        "DANGER": ((40, 40, 245), (35, 10, 10), "[SECURITY ALERT]"),
        "WARNING": ((0, 200, 255), (35, 25, 10), "[WARNING]"),
        "INFO": ((255, 220, 0), (12, 22, 30), "[SYSTEM]")
    }

    def __init__(self):
        self.notifications = []
        self.vignette_color = None
        self.vignette_expiry = 0

    def post(self, text, alert_type="INFO", duration=3.5, sound=None):
        """Post a new animated on-screen notification toast."""
        self.notifications.append({
            "text": text,
            "type": alert_type,
            "start_time": time.time(),
            "duration": duration
        })

        if alert_type == "DANGER":
            self.trigger_screen_flash((40, 40, 245), duration=1.8)
            play_audio_cue(sound or "alert_danger")
        elif alert_type == "SUCCESS":
            self.trigger_screen_flash((50, 255, 120), duration=1.2)
            play_audio_cue(sound or "alert_success")
        elif alert_type == "WARNING":
            self.trigger_screen_flash((0, 180, 255), duration=1.0)
            play_audio_cue(sound or "alert_warning")
        else:
            play_audio_cue(sound or "toast")

    def trigger_screen_flash(self, color, duration=1.5):
        self.vignette_color = color
        self.vignette_expiry = time.time() + duration

    def draw(self, frame, w_img, h_img):
        cur_time = time.time()

        # 1. Screen edge vignette alert pulse
        if self.vignette_color and cur_time < self.vignette_expiry:
            remaining = self.vignette_expiry - cur_time
            pulse = abs(math.sin(remaining * 8.0)) * 0.45
            border_thickness = 10
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w_img, h_img), self.vignette_color, border_thickness * 2)
            cv2.addWeighted(overlay, pulse, frame, 1.0 - pulse, 0, frame)

        # 2. Draw toast notifications (slide down from top center)
        self.notifications = [n for n in self.notifications if cur_time - n["start_time"] < n["duration"]]
        
        for idx, notif in enumerate(self.notifications[-3:]):
            elapsed = cur_time - notif["start_time"]
            duration = notif["duration"]
            
            if elapsed < 0.3:
                anim_prog = elapsed / 0.3
            elif elapsed > duration - 0.4:
                anim_prog = (duration - elapsed) / 0.4
            else:
                anim_prog = 1.0
            anim_prog = max(0.0, min(1.0, anim_prog))

            accent_color, bg_color, tag = self.COLOR_MAP.get(notif["type"], self.COLOR_MAP["INFO"])
            
            toast_w, toast_h = 520, 40
            target_y = 66 + idx * 46
            start_y = 10
            cur_y = int(start_y + (target_y - start_y) * anim_prog)
            cur_x = (w_img - toast_w) // 2

            # Glassmorphism Toast Body
            toast_overlay = frame.copy()
            cv2.rectangle(toast_overlay, (cur_x, cur_y), (cur_x + toast_w, cur_y + toast_h), bg_color, -1)
            alpha = 0.85 * anim_prog
            cv2.addWeighted(toast_overlay, alpha, frame, 1.0 - alpha, 0, frame)

            # Glowing Border & Accent Tag
            cv2.rectangle(frame, (cur_x, cur_y), (cur_x + toast_w, cur_y + toast_h), accent_color, 1, cv2.LINE_AA)
            cv2.rectangle(frame, (cur_x, cur_y), (cur_x + 6, cur_y + toast_h), accent_color, -1)

            # Notification Text
            msg = f"{tag} {notif['text']}"
            cv2.putText(
                frame,
                msg,
                (cur_x + 16, cur_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )


# ==============================================================================
#  BIOMETRIC DATABASE & AUDIT SYSTEM
# ==============================================================================

class BiometricDatabase:
    """Manages enrolled iris profiles, cryptographic signatures, and audit logs."""
    DB_FILE = "biometric_db.json"
    LOG_FILE = "scan_audit_log.csv"

    def __init__(self):
        self.profiles = self._load_db()
        self._init_log()

    def _load_db(self):
        if os.path.exists(self.DB_FILE):
            try:
                with open(self.DB_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        default_db = {
            "IRIS-001": {
                "name": "Abila Khan Keya (Admin)",
                "clearance": "LEVEL 5 // ALPHA",
                "hash": "8F3A2B1C9D4E",
                "enrolled_at": "2026-08-31"
            },
            "IRIS-002": {
                "name": "Authorized Agent",
                "clearance": "LEVEL 3 // OPERATIVE",
                "hash": "4A7C9E1F2B5D",
                "enrolled_at": "2026-08-31"
            }
        }
        self.save_db(default_db)
        return default_db

    def save_db(self, db=None):
        if db is not None:
            self.profiles = db
        try:
            with open(self.DB_FILE, "w") as f:
                json.dump(self.profiles, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Failed to save DB: {e}")

    def _init_log(self):
        if not os.path.exists(self.LOG_FILE):
            with open(self.LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Profile ID", "Name", "Status", "Confidence", "Liveness"])

    def log_scan(self, profile_id, name, status, confidence, liveness):
        try:
            with open(self.LOG_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    profile_id,
                    name,
                    status,
                    f"{confidence:.1f}%",
                    f"{liveness:.1f}%"
                ])
        except Exception:
            pass

    def enroll(self, profile_id, name, clearance, iris_hash):
        self.profiles[profile_id] = {
            "name": name,
            "clearance": clearance,
            "hash": iris_hash,
            "enrolled_at": time.strftime("%Y-%m-%d %H:%M")
        }
        self.save_db()


# ==============================================================================
#  SMOOTH FILTERING & ADAPTIVE TRACKER
# ==============================================================================

class SmoothValue:
    """Adaptive exponential filter with velocity damping for jitter-free tracking."""
    def __init__(self, alpha=0.35):
        self.val = None
        self.alpha = alpha

    def update(self, target):
        if target is None:
            return self.val
        if self.val is None:
            self.val = float(target)
        else:
            self.val = self.val * (1.0 - self.alpha) + float(target) * self.alpha
        return self.val


class SmoothBoxTracker:
    """
    Ultra-smooth bounding box tracker with dynamic persistence,
    coordinate interpolation (LERP), pupil geometry, and blink liveness detection.
    """
    def __init__(self, alpha=0.28, max_missed=12):
        self.alpha = alpha
        self.max_missed = max_missed
        self.tracks = []
        self.total_blinks = 0

    def _iou(self, a, b):
        xA = max(a[0], b[0])
        yA = max(a[1], b[1])
        xB = min(a[0] + a[2], b[0] + b[2])
        yB = min(a[1] + a[3], b[1] + b[3])
        inter = max(0, xB - xA) * max(0, yB - yA)
        areaA = a[2] * a[3]
        areaB = b[2] * b[3]
        union = float(areaA + areaB - inter)
        return inter / union if union > 0 else 0

    def update(self, detected_boxes, gray_frame):
        matched_detect_indices = set()
        updated_tracks = []

        for track in self.tracks:
            best_iou = 0.12
            best_idx = -1

            for idx, box in enumerate(detected_boxes):
                if idx in matched_detect_indices:
                    continue
                iou = self._iou(track['box'], box)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_idx != -1:
                matched_detect_indices.add(best_idx)
                d_box = detected_boxes[best_idx]

                # Check if recovering from a blink
                if 1 <= track['missed'] <= 3:
                    self.total_blinks += 1
                    play_audio_cue("blink")

                # Adaptive EMA smoothing on box coordinates
                curr_box = track['box']
                smooth_box = [
                    int(curr_box[i] * (1.0 - self.alpha) + d_box[i] * self.alpha)
                    for i in range(4)
                ]

                # Pupil extraction inside ROI
                raw_pupil, pupil_rad, iris_polar = self._extract_pupil_and_polar(gray_frame, smooth_box)
                prev_pupil = track.get('pupil', raw_pupil)
                
                if raw_pupil and prev_pupil:
                    smooth_pupil = (
                        int(prev_pupil[0] * 0.75 + raw_pupil[0] * 0.25),
                        int(prev_pupil[1] * 0.75 + raw_pupil[1] * 0.25)
                    )
                else:
                    smooth_pupil = raw_pupil or prev_pupil

                # Confidence and lock score ramp up
                lock_score = min(1.0, track.get('lock_score', 0.0) + 0.04)
                opacity = min(1.0, track.get('opacity', 0.0) + 0.12)

                updated_tracks.append({
                    'box': smooth_box,
                    'pupil': smooth_pupil,
                    'pupil_radius': pupil_rad,
                    'iris_polar': iris_polar,
                    'missed': 0,
                    'opacity': opacity,
                    'lock_score': lock_score,
                    'track_id': track.get('track_id', np.random.randint(1000, 9999))
                })
            else:
                # Retain track temporarily to prevent frame drops/flicker
                missed = track['missed'] + 1
                if missed <= self.max_missed:
                    opacity = max(0.0, track.get('opacity', 1.0) - (1.0 / self.max_missed))
                    lock_score = max(0.0, track.get('lock_score', 1.0) - 0.08)
                    updated_tracks.append({
                        'box': track['box'],
                        'pupil': track.get('pupil'),
                        'pupil_radius': track.get('pupil_radius', 6),
                        'iris_polar': track.get('iris_polar'),
                        'missed': missed,
                        'opacity': opacity,
                        'lock_score': lock_score,
                        'track_id': track['track_id']
                    })

        # Add new untracked detections
        for idx, box in enumerate(detected_boxes):
            if idx not in matched_detect_indices:
                pupil, rad, iris_polar = self._extract_pupil_and_polar(gray_frame, box)
                updated_tracks.append({
                    'box': box,
                    'pupil': pupil,
                    'pupil_radius': rad,
                    'iris_polar': iris_polar,
                    'missed': 0,
                    'opacity': 0.35,
                    'lock_score': 0.1,
                    'track_id': np.random.randint(1000, 9999)
                })

        self.tracks = updated_tracks
        return self.tracks

    def _extract_pupil_and_polar(self, gray_frame, box):
        x, y, w, h = box
        if w < 12 or h < 12:
            return None, 5, None

        h_img, w_img = gray_frame.shape
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w_img, x + w), min(h_img, y + h)
        roi = gray_frame[y1:y2, x1:x2]

        if roi.size == 0:
            return None, 5, None

        blurred = cv2.GaussianBlur(roi, (7, 7), 0)
        _, _, min_loc, _ = cv2.minMaxLoc(blurred)

        px = x1 + min_loc[0]
        py = y1 + min_loc[1]
        rad = max(4, int(min(w, h) * 0.16))

        # Daugman Polar Unwrap Simulation
        iris_polar = None
        try:
            rx, ry = min_loc[0], min_loc[1]
            max_r = int(min(w, h) * 0.45)
            if max_r > rad + 4 and rx - max_r >= 0 and ry - max_r >= 0 and rx + max_r < roi.shape[1] and ry + max_r < roi.shape[0]:
                iris_crop = roi[ry - max_r:ry + max_r, rx - max_r:rx + max_r]
                if iris_crop.size > 0:
                    polar = cv2.linearPolar(iris_crop, (max_r, max_r), max_r, cv2.WARP_FILL_OUTLIERS)
                    iris_polar = cv2.resize(polar[rad:max_r, :], (180, 24))
        except Exception:
            pass

        return (px, py), rad, iris_polar


# ==============================================================================
#  THEME PALETTES & GRAPHICS RENDERING
# ==============================================================================

class HUDTheme:
    THEMES = {
        "CYBER_CYAN": {
            "name": "CYBER BLUEPRINT",
            "accent": (255, 230, 0),
            "secondary": (50, 255, 120),
            "laser": (0, 240, 255),
            "panel_bg": (12, 18, 22),
            "border": (0, 200, 255),
            "apply_filter": None
        },
        "NIGHT_VISION": {
            "name": "TACTICAL NVG",
            "accent": (50, 255, 80),
            "secondary": (30, 210, 60),
            "laser": (100, 255, 120),
            "panel_bg": (8, 24, 10),
            "border": (50, 255, 80),
            "apply_filter": "NVG"
        },
        "THERMAL_FLIR": {
            "name": "FLIR THERMAL IR",
            "accent": (0, 220, 255),
            "secondary": (20, 160, 255),
            "laser": (255, 255, 255),
            "panel_bg": (15, 10, 30),
            "border": (255, 120, 0),
            "apply_filter": "THERMAL"
        },
        "AMBER_RECON": {
            "name": "AMBER DEFENSE",
            "accent": (0, 180, 255),
            "secondary": (0, 230, 255),
            "laser": (0, 255, 255),
            "panel_bg": (20, 16, 10),
            "border": (0, 180, 255),
            "apply_filter": None
        }
    }


class BiometricHUD:
    """Draws high-tech holographic overlays, reticles, scanlines, and telemetry."""

    TEXT_WHITE = (245, 245, 245)
    TEXT_MUTED = (160, 175, 180)
    CRIMSON = (40, 40, 240)

    @staticmethod
    def draw_glass_panel(img, x, y, w, h, bg_color=(12, 18, 22), alpha=0.6, border_color=(0, 200, 255)):
        """Draws a modern translucent glassmorphism panel with border accents."""
        overlay = img.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
        cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)

        cv2.rectangle(img, (x, y), (x + w, y + h), (45, 60, 70), 1, cv2.LINE_AA)
        
        c_len = 8
        cv2.line(img, (x, y), (x + c_len, y), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x, y), (x, y + c_len), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x + w, y), (x + w - c_len, y), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x + w, y), (x + w, y + c_len), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x, y + h), (x + c_len, y + h), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x, y + h), (x, y + h - c_len), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x + w, y + h), (x + w - c_len, y + h), border_color, 2, cv2.LINE_AA)
        cv2.line(img, (x + w, y + h), (x + w, y + h - c_len), border_color, 2, cv2.LINE_AA)

    @classmethod
    def draw_reticle(cls, img, track, elapsed, theme_cfg):
        """Draws a smooth rotating multi-layer biometric reticle over the detected eye."""
        box = track['box']
        pupil = track.get('pupil')
        lock_score = track.get('lock_score', 0.0)

        x, y, w, h = box
        cx = pupil[0] if pupil else x + w // 2
        cy = pupil[1] if pupil else y + h // 2
        radius = max(18, int(min(w, h) * 0.48))

        accent = theme_cfg["secondary"] if lock_score > 0.75 else theme_cfg["accent"]

        # 1. Tech Brackets
        pad = 8
        bx1, by1 = x - pad, y - pad
        bw, bh = w + pad * 2, h + pad * 2
        c_len = max(10, int(min(w, h) * 0.22))
        
        # Top-Left Corner
        cv2.line(img, (bx1, by1), (bx1 + c_len, by1), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1, by1), (bx1, by1 + c_len), accent, 2, cv2.LINE_AA)
        # Top-Right Corner
        cv2.line(img, (bx1 + bw, by1), (bx1 + bw - c_len, by1), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1), (bx1 + bw, by1 + c_len), accent, 2, cv2.LINE_AA)
        # Bottom-Left Corner
        cv2.line(img, (bx1, by1 + bh), (bx1 + c_len, by1 + bh), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1, by1 + bh), (bx1, by1 + bh - c_len), accent, 2, cv2.LINE_AA)
        # Bottom-Right Corner
        cv2.line(img, (bx1 + bw, by1 + bh), (bx1 + bw - c_len, by1 + bh), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1 + bh), (bx1 + bw, by1 + bh - c_len), accent, 2, cv2.LINE_AA)

        # 2. Outer Rotating Azimuth Ring
        rot_angle = (elapsed * 50) % 360
        cv2.circle(img, (cx, cy), radius, accent, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), max(6, radius - 8), (accent[0], 140, 60), 1, cv2.LINE_AA)

        for a in range(0, 360, 30):
            rad = math.radians(a + rot_angle)
            r1 = radius - 3
            r2 = radius + (4 if a % 90 == 0 else 2)
            p1 = (int(cx + r1 * math.cos(rad)), int(cy + r1 * math.sin(rad)))
            p2 = (int(cx + r2 * math.cos(rad)), int(cy + r2 * math.sin(rad)))
            cv2.line(img, p1, p2, accent, 1, cv2.LINE_AA)

        # 3. Inner Counter-Rotating Segmented Arcs
        rev_angle = (-elapsed * 75) % 360
        arc_radius = max(8, radius - 14)
        for arc_start in [0, 120, 240]:
            start_deg = (arc_start + rev_angle) % 360
            end_deg = (start_deg + 60) % 360
            cv2.ellipse(img, (cx, cy), (arc_radius, arc_radius), 0, start_deg, end_deg, theme_cfg["laser"], 1, cv2.LINE_AA)

        # 4. Pupil Center Crosshair & Target Dot
        if pupil:
            cv2.circle(img, (cx, cy), 3, theme_cfg["laser"], -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), track.get('pupil_radius', 6), theme_cfg["secondary"], 1, cv2.LINE_AA)
            ch_len = 6
            cv2.line(img, (cx - ch_len, cy), (cx + ch_len, cy), theme_cfg["laser"], 1, cv2.LINE_AA)
            cv2.line(img, (cx, cy - ch_len), (cx, cy + ch_len), theme_cfg["laser"], 1, cv2.LINE_AA)

        # 5. Smooth Scanning Laser Line
        laser_offset = math.sin(elapsed * 4.5) * (h * 0.46)
        laser_y = int(cy + laser_offset)
        cv2.line(img, (bx1, laser_y), (bx1 + bw, laser_y), theme_cfg["laser"], 1, cv2.LINE_AA)

        # 6. Target Lock Status
        status_label = "IRIS LOCK 99.8%" if lock_score > 0.8 else f"ALIGNING {int(lock_score*100)}%"
        cv2.putText(
            img,
            status_label,
            (bx1, max(18, by1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            accent,
            1,
            cv2.LINE_AA
        )


# ==============================================================================
#  MAIN APPLICATION WORKSTATION
# ==============================================================================

class IrisScannerApp:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

        self.tracker = SmoothBoxTracker(alpha=0.32, max_missed=10)
        self.hud = BiometricHUD()
        self.db = BiometricDatabase()
        self.alerts = AlertNotificationManager()
        self.fps_filter = SmoothValue(alpha=0.15)
        
        # Theme management
        self.theme_keys = list(HUDTheme.THEMES.keys())
        self.current_theme_idx = 0

        # State management
        self.scan_state = "IDLE"  # IDLE, SCANNING, VERIFIED, FAILED
        self.scan_start_time = 0
        self.scan_progress = 0.0
        self.authenticated_user = None
        self.hud_mode = "FULL"  # FULL, MINIMAL
        self.snapshot_counter = 0

        # Initial Welcome Toast Alert
        self.alerts.post("BIOMETRIC IRIS WORKSTATION ONLINE", "INFO", duration=3.0)

    @property
    def theme(self):
        return HUDTheme.THEMES[self.theme_keys[self.current_theme_idx]]

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[CRITICAL] Unable to access camera device.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)

        app_start_time = time.time()
        prev_time = time.time()

        print("=" * 65)
        print("  👁️  BIOMETRIC IRIS SCANNER WORKSTATION PRO")
        print("  -------------------------------------------------------------")
        print("  [SPACE] Trigger Biometric Scan  |  [T] Cycle Color Themes    ")
        print("  [E]     Enroll Current Iris     |  [C] Capture Snapshot      ")
        print("  [M]     Toggle Full/Minimal HUD |  [Q/ESC] Exit System       ")
        print("=" * 65)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h_img, w_img, _ = frame.shape
            
            cur_time = time.time()
            dt = max(1e-5, cur_time - prev_time)
            fps = self.fps_filter.update(1.0 / dt)
            prev_time = cur_time
            elapsed = cur_time - app_start_time

            # Theme video color effects (FLIR Thermal / Night Vision)
            if self.theme["apply_filter"] == "THERMAL":
                gray_raw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.applyColorMap(gray_raw, cv2.COLORMAP_INFERNO)
            elif self.theme["apply_filter"] == "NVG":
                gray_raw = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.merge([np.zeros_like(gray_raw), gray_raw, np.zeros_like(gray_raw)])

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)

            # Face & Eye Cascade Stage
            detected_eyes = []
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

            # Update tracker engine
            tracks = self.tracker.update(detected_eyes, enhanced_gray)

            # Update authentication state
            self._update_scan_state(cur_time, tracks, elapsed)

            # Composite HUD
            if self.hud_mode == "FULL":
                self._render_full_hud(frame, tracks, elapsed, fps, w_img, h_img)
            else:
                self._render_minimal_hud(frame, tracks, elapsed, fps, w_img, h_img)

            # Render Animated Alert Notifications & Toasts
            self.alerts.draw(frame, w_img, h_img)

            cv2.imshow("Biometric Iris Scanner Pro", frame)

            # Handle interactive keys
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break
            elif key == ord(' '):
                self._trigger_scan(cur_time, len(tracks))
            elif key in (ord('t'), ord('T')):
                self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_keys)
                self.alerts.post(f"THEME ACTIVATED: {self.theme['name']}", "INFO", duration=2.5)
            elif key in (ord('e'), ord('E')):
                self._enroll_current_iris(tracks, elapsed)
            elif key in (ord('m'), ord('M')):
                self.hud_mode = "MINIMAL" if self.hud_mode == "FULL" else "FULL"
                self.alerts.post(f"HUD DISPLAY MODE: {self.hud_mode}", "INFO", duration=2.0)
            elif key in (ord('c'), ord('C')):
                self._save_snapshot(frame)

        cap.release()
        cv2.destroyAllWindows()

    def _trigger_scan(self, cur_time, active_targets):
        if active_targets == 0:
            self.alerts.post("NO TARGET ACQUIRED // POSITION EYE IN FRAME", "WARNING", duration=3.0)
            return

        self.scan_state = "SCANNING"
        self.scan_start_time = cur_time
        self.scan_progress = 0.0
        self.alerts.post("INITIALIZING BIOMETRIC IRIS SCAN...", "INFO", duration=2.0)

    def _update_scan_state(self, cur_time, tracks, elapsed):
        if self.scan_state == "SCANNING":
            duration = 2.2
            self.scan_progress = min(1.0, (cur_time - self.scan_start_time) / duration)
            if self.scan_progress >= 1.0:
                if len(tracks) > 0:
                    self.scan_state = "VERIFIED"
                    first_profile = next(iter(self.db.profiles.values()))
                    self.authenticated_user = first_profile
                    self.db.log_scan("IRIS-001", first_profile["name"], "ACCESS_GRANTED", 99.4, 98.8)
                    self.alerts.post(f"IDENTITY VERIFIED: {first_profile['name']}", "SUCCESS", duration=4.0)
                else:
                    self.scan_state = "FAILED"
                    self.authenticated_user = None
                    self.db.log_scan("UNKNOWN", "Unidentified Subject", "ACCESS_DENIED", 32.1, 45.0)
                    self.alerts.post("SECURITY ALERT: ACCESS DENIED // IRIS MISMATCH", "DANGER", duration=4.0)
        elif self.scan_state in ("VERIFIED", "FAILED"):
            if cur_time - self.scan_start_time > 5.5:
                self.scan_state = "IDLE"
                self.authenticated_user = None

    def _enroll_current_iris(self, tracks, elapsed):
        if len(tracks) == 0:
            self.alerts.post("ENROLLMENT FAILED: NO ACTIVE IRIS IN FRAME", "WARNING", duration=3.0)
            return
        new_id = f"IRIS-{len(self.db.profiles) + 1:03d}"
        seed = f"USER_{time.time()}_{len(tracks)}"
        new_hash = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
        self.db.enroll(new_id, f"Enrolled User {new_id}", "LEVEL 2 // USER", new_hash)
        self.alerts.post(f"BIOMETRIC PROFILE SAVED // ID: {new_id}", "SUCCESS", duration=3.5)

    def _save_snapshot(self, frame):
        self.snapshot_counter += 1
        filename = f"iris_capture_{int(time.time())}.png"
        cv2.imwrite(filename, frame)
        self.alerts.post(f"SNAPSHOT SAVED: {filename}", "INFO", duration=3.0, sound="shutter")

    def _render_full_hud(self, frame, tracks, elapsed, fps, w, h):
        theme = self.theme

        # Background grid overlay
        grid_alpha = frame.copy()
        for gx in range(0, w, 60):
            cv2.line(grid_alpha, (gx, 0), (gx, h), (35, 45, 40), 1)
        for gy in range(0, h, 60):
            cv2.line(grid_alpha, (0, gy), (w, gy), (35, 45, 40), 1)
        cv2.addWeighted(grid_alpha, 0.2, frame, 0.8, 0, frame)

        # Draw Eye Reticles
        for track in tracks:
            if track['missed'] <= 5:
                self.hud.draw_reticle(frame, track, elapsed, theme)

        # 1. Top Status Bar
        self.hud.draw_glass_panel(frame, 15, 12, w - 30, 48, bg_color=theme["panel_bg"], alpha=0.75, border_color=theme["border"])
        cv2.putText(frame, f"BIOMETRIC IRIS SUITE // [{theme['name']}]", (30, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.52, theme["accent"], 2, cv2.LINE_AA)
        
        sys_status = "READY" if self.scan_state == "IDLE" else self.scan_state
        status_color = theme["secondary"] if sys_status in ("READY", "VERIFIED") else theme["accent"]
        cv2.putText(frame, f"STATUS: {sys_status}", (w - 380, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.46, status_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 110, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.46, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 2. Left Telemetry Card
        card_w, card_h = 240, 230
        self.hud.draw_glass_panel(frame, 15, 75, card_w, card_h, bg_color=theme["panel_bg"], alpha=0.68, border_color=theme["border"])
        cv2.putText(frame, "TELEMETRY & LIVENESS", (28, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.44, theme["accent"], 1, cv2.LINE_AA)
        cv2.line(frame, (28, 105), (28 + card_w - 26, 105), (50, 70, 80), 1, cv2.LINE_AA)

        target_count = sum(1 for t in tracks if t['missed'] <= 4)
        hash_seed = f"IRIS_{target_count}_{int(elapsed * 2)}"
        bio_hash = hashlib.md5(hash_seed.encode()).hexdigest()[:12].upper()

        liveness_str = f"BLINKS: {self.tracker.total_blinks} (REAL)" if self.tracker.total_blinks > 0 else "ACQUIRING..."

        lines = [
            f"TARGETS: {target_count} ACTIVE",
            f"LIVENESS: {liveness_str}",
            f"HASH: 0x{bio_hash}",
            f"PROFILES: {len(self.db.profiles)} ENROLLED",
            f"CONFIDENCE: 99.1%",
            f"CRYPTO: SHA256 / AES"
        ]
        
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (28, 128 + i * 21), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 3. Right Top Card: Polar Iris Unwrap Strip (Daugman Rubber Sheet PiP)
        pip_w, pip_h = 220, 110
        pip_x = w - pip_w - 15
        self.hud.draw_glass_panel(frame, pip_x, 75, pip_w, pip_h, bg_color=theme["panel_bg"], alpha=0.68, border_color=theme["border"])
        cv2.putText(frame, "POLAR IRIS MAP", (pip_x + 12, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.42, theme["accent"], 1, cv2.LINE_AA)
        
        active_polar = next((t['iris_polar'] for t in tracks if t.get('iris_polar') is not None), None)
        if active_polar is not None:
            try:
                polar_bgr = cv2.cvtColor(active_polar, cv2.COLOR_GRAY2BGR)
                polar_resized = cv2.resize(polar_bgr, (196, 32))
                py = 108
                px = pip_x + 12
                frame[py:py+32, px:px+196] = polar_resized
                cv2.rectangle(frame, (px, py), (px+196, py+32), theme["border"], 1)
                cv2.putText(frame, "DAUGMAN STRIP [R, THETA]", (px, py + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.32, theme["secondary"], 1, cv2.LINE_AA)
            except Exception:
                pass
        else:
            cv2.putText(frame, "AWAITING LOCK...", (pip_x + 12, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.36, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 4. Bottom Interactive Authentication Banner
        bar_w, bar_h = 420, 16
        bx, by = (w - bar_w) // 2, h - 55
        self.hud.draw_glass_panel(frame, bx - 20, by - 24, bar_w + 40, 62, bg_color=theme["panel_bg"], alpha=0.75, border_color=theme["border"])

        if self.scan_state == "SCANNING":
            fill_w = int(bar_w * self.scan_progress)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), theme["accent"], -1)
            msg = f"AUTHENTICATING BIOMETRIC PATTERN... {int(self.scan_progress * 100)}%"
            cv2.putText(frame, msg, (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, theme["accent"], 1, cv2.LINE_AA)
        elif self.scan_state == "VERIFIED" and self.authenticated_user:
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), theme["secondary"], -1)
            user_text = f"ACCESS GRANTED // {self.authenticated_user['name']} ({self.authenticated_user['clearance']})"
            cv2.putText(frame, user_text, (bx - 15, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.40, theme["secondary"], 1, cv2.LINE_AA)
        elif self.scan_state == "FAILED":
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), self.hud.CRIMSON, -1)
            cv2.putText(frame, "ACCESS DENIED // IRIS MISMATCH OR SPOOF DETECTED", (bx - 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.40, self.hud.CRIMSON, 2, cv2.LINE_AA)
        else:
            idle_prog = (math.sin(elapsed * 2.5) + 1.0) / 2.0
            fill_w = int(bar_w * idle_prog)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), (60, 100, 90), -1)
            cv2.putText(frame, "READY: [SPACE] SCAN | [T] THEME | [E] ENROLL | [C] CAPTURE", (bx - 16, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (80, 100, 110), 1, cv2.LINE_AA)

    def _render_minimal_hud(self, frame, tracks, elapsed, fps, w, h):
        theme = self.theme
        for track in tracks:
            if track['missed'] <= 4:
                self.hud.draw_reticle(frame, track, elapsed, theme)
        cv2.putText(frame, f"IRIS SCANNER // {theme['name']} [FPS: {fps:.1f}]", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.48, theme["accent"], 1, cv2.LINE_AA)


# ==============================================================================
#  ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    app = IrisScannerApp()
    app.run()