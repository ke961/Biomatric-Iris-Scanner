import cv2
import numpy as np
import time
import math

def main():
    width, height = 600, 600
    start_time = time.time()

    print("Running Smooth Iris Scan Animation Demo. Press 'q' or 'ESC' to exit.")

    while True:
        elapsed = time.time() - start_time
        img = np.zeros((height, width, 3), dtype=np.uint8)
        cx, cy = width // 2, height // 2

        # Background grid
        grid_color = (20, 30, 25)
        for gx in range(0, width, 40):
            cv2.line(img, (gx, 0), (gx, height), grid_color, 1, cv2.LINE_AA)
        for gy in range(0, height, 40):
            cv2.line(img, (0, gy), (width, gy), grid_color, 1, cv2.LINE_AA)

        # Rotating outer ring with notches
        rot_angle = (elapsed * 45) % 360
        r_outer = 180
        cv2.circle(img, (cx, cy), r_outer, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r_outer - 15, (0, 140, 180), 1, cv2.LINE_AA)

        for a in range(0, 360, 15):
            rad = math.radians(a + rot_angle)
            p1 = (int(cx + (r_outer - 8) * math.cos(rad)), int(cy + (r_outer - 8) * math.sin(rad)))
            p2 = (int(cx + r_outer * math.cos(rad)), int(cy + r_outer * math.sin(rad)))
            cv2.line(img, p1, p2, (0, 230, 255), 1, cv2.LINE_AA)

        # Counter-rotating iris texture lines
        for a in range(0, 360, 20):
            rad = math.radians(a - rot_angle * 1.5)
            p1 = (int(cx + 60 * math.cos(rad)), int(cy + 60 * math.sin(rad)))
            p2 = (int(cx + 140 * math.cos(rad)), int(cy + 140 * math.sin(rad)))
            cv2.line(img, p1, p2, (100, 255, 100), 1, cv2.LINE_AA)

        # Concentric pulsating circles
        pulse = math.sin(elapsed * 3) * 5
        cv2.circle(img, (cx, cy), int(120 + pulse), (0, 255, 180), 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), int(80 + pulse * 0.5), (0, 255, 120), 1, cv2.LINE_AA)

        # Pupil
        pupil_radius = int(45 + math.sin(elapsed * 2) * 4)
        cv2.circle(img, (cx, cy), pupil_radius, (15, 15, 20), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), pupil_radius, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.circle(img, (cx - 10, cy - 10), 8, (255, 255, 255), -1, cv2.LINE_AA)  # Specular highlight

        # Smooth vertical laser scan line
        laser_y = int(cy + math.sin(elapsed * 3.5) * (r_outer - 10))
        cv2.line(img, (cx - r_outer, laser_y), (cx + r_outer, laser_y), (0, 255, 255), 2, cv2.LINE_AA)

        # HUD Text
        scan_pct = int(((math.sin(elapsed * 2) + 1.0) / 2.0) * 100)
        cv2.putText(img, "BIOMETRIC IRIS SCANNER", (120, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 220), 2, cv2.LINE_AA)
        cv2.putText(img, f"STATUS: SCANNING ({scan_pct}%)", (170, 540), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 120), 1, cv2.LINE_AA)

        cv2.imshow("Iris Scan Demo", img)

        key = cv2.waitKey(16) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()