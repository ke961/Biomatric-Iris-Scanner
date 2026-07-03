# 👁️ Iris Scanner Simulation Using OpenCV

## Project Overview

This project is a real-time eye detection application developed using **Python** and **OpenCV**. It uses the computer's webcam to detect human eyes and simulates an iris scanning system by highlighting the detected eye region.

The application demonstrates the basic concepts of computer vision, object detection, and real-time image processing.

---

## Features

- Real-time webcam capture
- Eye detection using Haar Cascade Classifier
- Green bounding box around detected eyes
- "Eye Detected" status display
- Live video processing
- Exit using the ESC key

---

## Project Structure

```
IrisScanner/
│
├── iris_scanner.py      # Main Python program
├── README.md            # Project documentation
└── requirements.txt     # Required Python libraries
```

---

## Technologies Used

- Python 3
- OpenCV
- Haar Cascade Classifier

---

## Requirements

Install the required library:

```bash
pip install opencv-python
```

Or install from the requirements file:

```bash
pip install -r requirements.txt
```

---

## How It Works

1. Opens the webcam.
2. Captures live video frames.
3. Converts each frame to grayscale.
4. Detects eyes using the Haar Cascade classifier.
5. Draws a green rectangle around each detected eye.
6. Displays the detection result in real time.
7. Press **ESC** to close the application.

---

## How to Run

Run the following command:

```bash
python iris_scanner.py
```

---

## Expected Output

- Webcam opens automatically.
- Eyes are detected in real time.
- Green rectangles appear around detected eyes.
- "Eye Detected" is displayed above each detected eye.
- Press **ESC** to exit.

---

## Future Improvements

- Iris recognition instead of simple eye detection
- User authentication system
- Blink detection for liveness verification
- Save scan history
- Database integration
- Face detection before iris scanning
- GUI using Tkinter or CustomTkinter
- Authentication confidence score
- User registration and login
- Screenshot capture

---

## Limitations

This project detects the **eye region only**. It does **not** perform actual biometric iris recognition or identity verification. It is intended as a demonstration of real-time eye detection using computer vision.

---

## Author

Keya
