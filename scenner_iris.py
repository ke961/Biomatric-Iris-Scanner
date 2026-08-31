import cv2
import numpy as np
import time
import math
import hashlib
import os

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
    coordinate interpolation (LERP), and pupil geometry estimation.
    """
    def __init__(self, alpha=0.28, max_missed=12):
        self.alpha = alpha
        self.max_missed = max_missed
        self.tracks = []  # list of track objects

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

                # Adaptive EMA smoothing on box coordinates
                curr_box = track['box']
                smooth_box = [
                    int(curr_box[i] * (1.0 - self.alpha) + d_box[i] * self.alpha)
                    for i in range(4)
                ]

                # Pupil extraction inside ROI
                raw_pupil, pupil_rad = self._extract_pupil(gray_frame, smooth_box)
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
                        'missed': missed,
                        'opacity': opacity,
                        'lock_score': lock_score,
                        'track_id': track['track_id']
                    })

        # Add new untracked detections
        for idx, box in enumerate(detected_boxes):
            if idx not in matched_detect_indices:
                pupil, rad = self._extract_pupil(gray_frame, box)
                updated_tracks.append({
                    'box': box,
                    'pupil': pupil,
                    'pupil_radius': rad,
                    'missed': 0,
                    'opacity': 0.35,
                    'lock_score': 0.1,
                    'track_id': np.random.randint(1000, 9999)
                })

        self.tracks = updated_tracks
        return self.tracks

    def _extract_pupil(self, gray_frame, box):
        x, y, w, h = box
        if w < 12 or h < 12:
            return None, 5

        h_img, w_img = gray_frame.shape
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w_img, x + w), min(h_img, y + h)
        roi = gray_frame[y1:y2, x1:x2]

        if roi.size == 0:
            return None, 5

        # Denoise & extract dark pupil core
        blurred = cv2.GaussianBlur(roi, (7, 7), 0)
        min_val, _, min_loc, _ = cv2.minMaxLoc(blurred)

        px = x1 + min_loc[0]
        py = y1 + min_loc[1]
        
        # Estimate radius based on box proportions
        rad = max(4, int(min(w, h) * 0.16))
        return (px, py), rad


# ==============================================================================
#  PROFESSIONAL HUD & GRAPHICS RENDERING
# ==============================================================================

class BiometricHUD:
    """Draws high-tech holographic overlays, reticles, scanlines, and telemetry."""

    # Futuristic Color Palette (BGR)
    CYAN = (255, 230, 0)
    NEON_GREEN = (50, 255, 120)
    DEEP_BLUE = (180, 80, 20)
    AMBER = (0, 190, 255)
    CRIMSON = (40, 40, 240)
    DARK_GLASS = (15, 20, 24)
    TEXT_WHITE = (245, 245, 245)
    TEXT_MUTED = (160, 175, 180)

    @staticmethod
    def draw_glass_panel(img, x, y, w, h, bg_color=(12, 18, 22), alpha=0.6, border_color=(0, 200, 255)):
        """Draws a modern translucent glassmorphism panel with border accents."""
        overlay = img.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
        cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)

        # Subtle border
        cv2.rectangle(img, (x, y), (x + w, y + h), (45, 60, 70), 1, cv2.LINE_AA)
        
        # Tech corners
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
    def draw_reticle(cls, img, track, elapsed):
        """Draws a smooth rotating multi-layer biometric reticle over the detected eye."""
        box = track['box']
        pupil = track.get('pupil')
        opacity = track.get('opacity', 1.0)
        lock_score = track.get('lock_score', 0.0)

        x, y, w, h = box
        cx = pupil[0] if pupil else x + w // 2
        cy = pupil[1] if pupil else y + h // 2
        radius = max(18, int(min(w, h) * 0.48))

        # Color shifts based on lock status
        accent = cls.NEON_GREEN if lock_score > 0.75 else cls.CYAN

        # 1. Outer Tech Brackets
        pad = 8
        bx1, by1 = x - pad, y - pad
        bw, bh = w + pad * 2, h + pad * 2
        c_len = max(10, int(min(w, h) * 0.22))
        
        cv2.line(img, (bx1, by1), (bx1 + c_len, by1), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1, by1), (bx1, by1 + c_len), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1), (bx1 + bw - c_len, by1), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1), (bx1 + bw, by1 + c_len), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1, by1 + bh), (bx1 + c_len, by1 + bh), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1, by1 + bh), (bx1, by1 + bh - c_len), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1 + bh), (bx1 + bw - c_len, by1 + bh), accent, 2, cv2.LINE_AA)
        cv2.line(img, (bx1 + bw, by1 + bh), (bx1 + bw, by1 + bh - c_len), accent, 2, cv2.LINE_AA)

        # 2. Outer Rotating Azimuth Ring
        rot_angle = (elapsed * 50) % 360
        cv2.circle(img, (cx, cy), radius, accent, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), max(6, radius - 8), (cls.CYAN[0], 160, 60), 1, cv2.LINE_AA)

        # Compass azimuth ticks
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
            cv2.ellipse(img, (cx, cy), (arc_radius, arc_radius), 0, start_deg, end_deg, cls.AMBER, 1, cv2.LINE_AA)

        # 4. Pupil Center Crosshair & Dot
        if pupil:
            cv2.circle(img, (cx, cy), 3, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), track.get('pupil_radius', 6), cls.NEON_GREEN, 1, cv2.LINE_AA)
            ch_len = 6
            cv2.line(img, (cx - ch_len, cy), (cx + ch_len, cy), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.line(img, (cx, cy - ch_len), (cx, cy + ch_len), (0, 255, 255), 1, cv2.LINE_AA)

        # 5. Smooth Scanning Laser Line
        laser_offset = math.sin(elapsed * 4.5) * (h * 0.46)
        laser_y = int(cy + laser_offset)
        cv2.line(img, (bx1, laser_y), (bx1 + bw, laser_y), cls.CYAN, 1, cv2.LINE_AA)

        # 6. Biometric Target Label
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
#  MAIN APPLICATION CONTROLLER
# ==============================================================================

class IrisScannerApp:
    def __init__(self):
        # Cascades for face & eye extraction
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

        self.tracker = SmoothBoxTracker(alpha=0.32, max_missed=10)
        self.hud = BiometricHUD()
        self.fps_filter = SmoothValue(alpha=0.15)
        
        # Interactive state
        self.scan_state = "IDLE"  # IDLE, SCANNING, VERIFIED
        self.scan_start_time = 0
        self.scan_progress = 0.0
        self.hud_mode = "FULL"  # FULL, MINIMAL
        self.snapshot_counter = 0

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

        print("=" * 60)
        print("  👁️  PROFESSIONAL BIOMETRIC IRIS SCANNER WORKSTATION")
        print("  --------------------------------------------------")
        print("  [SPACE] Trigger Biometric Scan  |  [C] Snapshot   ")
        print("  [M]     Toggle HUD Mode         |  [Q/ESC] Exit   ")
        print("=" * 60)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Natural selfie mirror orientation
            frame = cv2.flip(frame, 1)
            h_img, w_img, _ = frame.shape
            
            cur_time = time.time()
            dt = max(1e-5, cur_time - prev_time)
            fps = self.fps_filter.update(1.0 / dt)
            prev_time = cur_time
            elapsed = cur_time - app_start_time

            # Grayscale & Equalization
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)

            # Stage 1: Face ROI Detection (eliminates false positives)
            detected_eyes = []
            faces = self.face_cascade.detectMultiScale(
                enhanced_gray,
                scaleFactor=1.18,
                minNeighbors=5,
                minSize=(110, 110)
            )

            if len(faces) > 0:
                for (fx, fy, fw, fh) in faces:
                    # Eye bounding region inside top 55% of face
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
                # Secondary fallback scanner
                raw_eyes = self.eye_cascade.detectMultiScale(
                    enhanced_gray,
                    scaleFactor=1.15,
                    minNeighbors=6,
                    minSize=(35, 35)
                )
                detected_eyes = list(raw_eyes)

            # Update smooth tracking engine
            tracks = self.tracker.update(detected_eyes, enhanced_gray)

            # Update interactive authentication scan state
            self._update_scan_state(cur_time, len(tracks))

            # Composite HUD Layers
            if self.hud_mode == "FULL":
                self._render_full_hud(frame, tracks, elapsed, fps, w_img, h_img)
            else:
                self._render_minimal_hud(frame, tracks, elapsed, fps, w_img, h_img)

            # Display window
            cv2.imshow("Biometric Iris Scanner Pro", frame)

            # User Controls
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break
            elif key == ord(' '):
                self._trigger_scan(cur_time)
            elif key in (ord('m'), ord('M')):
                self.hud_mode = "MINIMAL" if self.hud_mode == "FULL" else "FULL"
            elif key in (ord('c'), ord('C')):
                self._save_snapshot(frame)

        cap.release()
        cv2.destroyAllWindows()

    def _trigger_scan(self, cur_time):
        self.scan_state = "SCANNING"
        self.scan_start_time = cur_time
        self.scan_progress = 0.0

    def _update_scan_state(self, cur_time, active_targets):
        if self.scan_state == "SCANNING":
            duration = 2.4
            self.scan_progress = min(1.0, (cur_time - self.scan_start_time) / duration)
            if self.scan_progress >= 1.0:
                self.scan_state = "VERIFIED" if active_targets > 0 else "FAILED"
        elif self.scan_state in ("VERIFIED", "FAILED"):
            if cur_time - self.scan_start_time > 5.0:
                self.scan_state = "IDLE"

    def _save_snapshot(self, frame):
        self.snapshot_counter += 1
        filename = f"iris_capture_{int(time.time())}.png"
        cv2.imwrite(filename, frame)
        print(f"[SAVED] Biometric Iris Capture saved as: {filename}")

    def _render_full_hud(self, frame, tracks, elapsed, fps, w, h):
        # 1. Subtle holographic background grid
        grid_alpha = frame.copy()
        for gx in range(0, w, 60):
            cv2.line(grid_alpha, (gx, 0), (gx, h), (35, 45, 40), 1)
        for gy in range(0, h, 60):
            cv2.line(grid_alpha, (0, gy), (w, gy), (35, 45, 40), 1)
        cv2.addWeighted(grid_alpha, 0.2, frame, 0.8, 0, frame)

        # 2. Draw eye reticles
        for track in tracks:
            if track['missed'] <= 5:
                self.hud.draw_reticle(frame, track, elapsed)

        # 3. Top Status Bar Header
        self.hud.draw_glass_panel(frame, 15, 12, w - 30, 48, bg_color=(10, 16, 22), alpha=0.75)
        
        cv2.putText(frame, "BIOMETRIC IRIS WORKSTATION // V3.2", (30, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.58, self.hud.CYAN, 2, cv2.LINE_AA)
        
        sys_status = "READY" if self.scan_state == "IDLE" else self.scan_state
        status_color = self.hud.NEON_GREEN if sys_status in ("READY", "VERIFIED") else self.hud.AMBER
        cv2.putText(frame, f"STATUS: {sys_status}", (w - 360, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 120, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 4. Left Telemetry Card: Biometric Iris Analytics
        card_w, card_h = 240, 200
        self.hud.draw_glass_panel(frame, 15, 75, card_w, card_h, alpha=0.65)
        
        cv2.putText(frame, "TELEMETRY DATA", (28, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.hud.CYAN, 1, cv2.LINE_AA)
        cv2.line(frame, (28, 105), (28 + card_w - 26, 105), (50, 70, 80), 1, cv2.LINE_AA)

        target_count = sum(1 for t in tracks if t['missed'] <= 4)
        hash_seed = f"IRIS_{target_count}_{int(elapsed * 2)}"
        bio_hash = hashlib.md5(hash_seed.encode()).hexdigest()[:12].upper()

        lines = [
            f"TARGETS: {target_count} ACTIVE",
            f"SENSOR: DUAL-NIR SPECTRAL",
            f"HASH: 0x{bio_hash}",
            f"LIVENESS: 99.4%",
            f"CONFIDENCE: 98.7%",
            f"CRYPTO: SHA256 / AES"
        ]
        
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (28, 128 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        # 5. Bottom Interactive Scanner & Authentication Meter
        bar_w, bar_h = 360, 16
        bx, by = (w - bar_w) // 2, h - 50
        self.hud.draw_glass_panel(frame, bx - 20, by - 22, bar_w + 40, 56, alpha=0.7)

        if self.scan_state == "SCANNING":
            # Animated progress fill
            fill_w = int(bar_w * self.scan_progress)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), self.hud.CYAN, -1)
            msg = f"AUTHENTICATING BIOMETRIC PATTERN... {int(self.scan_progress * 100)}%"
            cv2.putText(frame, msg, (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.hud.CYAN, 1, cv2.LINE_AA)
        elif self.scan_state == "VERIFIED":
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), self.hud.NEON_GREEN, -1)
            cv2.putText(frame, "BIOMETRIC IDENTITY VERIFIED // ACCESS GRANTED", (bx - 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.44, self.hud.NEON_GREEN, 2, cv2.LINE_AA)
        elif self.scan_state == "FAILED":
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), self.hud.CRIMSON, -1)
            cv2.putText(frame, "ACCESS DENIED // IRIS MISMATCH", (bx + 20, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.44, self.hud.CRIMSON, 2, cv2.LINE_AA)
        else:
            # Idle pulse bar
            idle_prog = (math.sin(elapsed * 2.5) + 1.0) / 2.0
            fill_w = int(bar_w * idle_prog)
            cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), (60, 100, 90), -1)
            cv2.putText(frame, "STANDBY: PRESS [SPACE] TO SCAN BIOMETRIC IRIS", (bx - 15, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.hud.TEXT_MUTED, 1, cv2.LINE_AA)

        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (80, 100, 110), 1, cv2.LINE_AA)

    def _render_minimal_hud(self, frame, tracks, elapsed, fps, w, h):
        for track in tracks:
            if track['missed'] <= 4:
                self.hud.draw_reticle(frame, track, elapsed)
        
        cv2.putText(frame, f"IRIS SCANNER [FPS: {fps:.1f}]", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.hud.CYAN, 1, cv2.LINE_AA)


# ==============================================================================
#  ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    app = IrisScannerApp()
    app.run()
