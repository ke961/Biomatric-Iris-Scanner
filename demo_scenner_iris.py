import cv2
import numpy as np
import time
import math

THEMES = [
    {"name": "CYBER BLUEPRINT", "accent": (255, 230, 0), "sec": (0, 255, 128), "laser": (0, 255, 255)},
    {"name": "TACTICAL NVG", "accent": (50, 255, 80), "sec": (30, 210, 60), "laser": (100, 255, 120)},
    {"name": "FLIR THERMAL", "accent": (0, 200, 255), "sec": (20, 160, 255), "laser": (255, 255, 255)},
    {"name": "AMBER DEFENSE", "accent": (0, 180, 255), "sec": (0, 240, 255), "laser": (0, 255, 255)},
]

def main():
    width, height = 640, 640
    start_time = time.time()
    theme_idx = 0

    print("=" * 60)
    print("  👁️  BIOMETRIC IRIS SCANNER SIMULATION DEMO")
    print("  [T] Cycle Themes | [Q/ESC] Exit")
    print("=" * 60)

    while True:
        theme = THEMES[theme_idx]
        elapsed = time.time() - start_time
        img = np.zeros((height, width, 3), dtype=np.uint8)
        cx, cy = width // 2, height // 2

        # Background grid
        grid_color = (20, 28, 25)
        for gx in range(0, width, 40):
            cv2.line(img, (gx, 0), (gx, height), grid_color, 1, cv2.LINE_AA)
        for gy in range(0, height, 40):
            cv2.line(img, (0, gy), (width, gy), grid_color, 1, cv2.LINE_AA)

        # Rotating outer ring with degree notches
        rot_angle = (elapsed * 45) % 360
        r_outer = 190
        cv2.circle(img, (cx, cy), r_outer, theme["accent"], 2, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r_outer - 15, (40, 70, 80), 1, cv2.LINE_AA)

        for a in range(0, 360, 15):
            rad = math.radians(a + rot_angle)
            p1 = (int(cx + (r_outer - 8) * math.cos(rad)), int(cy + (r_outer - 8) * math.sin(rad)))
            p2 = (int(cx + r_outer * math.cos(rad)), int(cy + r_outer * math.sin(rad)))
            cv2.line(img, p1, p2, theme["accent"], 1, cv2.LINE_AA)

        # Counter-rotating iris texture lines
        for a in range(0, 360, 18):
            rad = math.radians(a - rot_angle * 1.6)
            p1 = (int(cx + 60 * math.cos(rad)), int(cy + 60 * math.sin(rad)))
            p2 = (int(cx + 150 * math.cos(rad)), int(cy + 150 * math.sin(rad)))
            cv2.line(img, p1, p2, theme["sec"], 1, cv2.LINE_AA)

        # Concentric pulsating circles
        pulse = math.sin(elapsed * 3) * 6
        cv2.circle(img, (cx, cy), int(130 + pulse), theme["sec"], 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), int(85 + pulse * 0.5), theme["accent"], 1, cv2.LINE_AA)

        # Pupil & Specular Reflection
        pupil_radius = int(46 + math.sin(elapsed * 2) * 4)
        cv2.circle(img, (cx, cy), pupil_radius, (12, 14, 18), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), pupil_radius, theme["laser"], 2, cv2.LINE_AA)
        cv2.circle(img, (cx - 12, cy - 12), 8, (255, 255, 255), -1, cv2.LINE_AA)

        # Vertical scanning laser beam
        laser_y = int(cy + math.sin(elapsed * 3.5) * (r_outer - 12))
        cv2.line(img, (cx - r_outer, laser_y), (cx + r_outer, laser_y), theme["laser"], 2, cv2.LINE_AA)

        # Top HUD Header
        cv2.putText(img, f"BIOMETRIC IRIS SIMULATION // [{theme['name']}]", (80, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, theme["accent"], 2, cv2.LINE_AA)

        # Bottom HUD Status
        scan_pct = int(((math.sin(elapsed * 2) + 1.0) / 2.0) * 100)
        status_text = f"AUTHENTICATING: {scan_pct}% | [T] SWITCH THEME"
        cv2.putText(img, status_text, (130, height - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, theme["sec"], 1, cv2.LINE_AA)

        cv2.imshow("Iris Scan Demo", img)

        key = cv2.waitKey(16) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break
        elif key in (ord('t'), ord('T')):
            theme_idx = (theme_idx + 1) % len(THEMES)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
