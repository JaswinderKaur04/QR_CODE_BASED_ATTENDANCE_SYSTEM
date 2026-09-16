"""
QR Code scanner module.
Uses OpenCV and pyzbar to detect and decode QR codes from a webcam feed.
"""
import cv2
from pyzbar.pyzbar import decode
from datetime import datetime
import time


class QRScanner:
    """Handles webcam-based QR code scanning."""

    def __init__(self, camera_index=0, resolution=(640, 480)):
        """
        Initialize the scanner.

        Args:
            camera_index (int): Index of the webcam to use (default 0).
            resolution (tuple): Desired resolution (width, height).
        """
        self.camera_index = camera_index
        self.resolution = resolution
        self.cap = None
        self.last_scanned_data = None
        self.last_scan_time = 0
        self.cooldown = 2  # seconds between scans of the same code

    def start(self):
        """Open the webcam."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera at index {self.camera_index}")

        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

    def stop(self):
        """Release the webcam."""
        if self.cap:
            self.cap.release()
            self.cap = None

    def read_frame(self):
        """
        Read a single frame from the webcam.

        Returns:
            numpy.ndarray or None: The captured frame, or None if failed.
        """
        if self.cap is None:
            self.start()

        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def scan_qr_code(self, frame):
        """
        Scan a frame for QR codes and return the decoded data.

        Args:
            frame (numpy.ndarray): The frame to scan.

        Returns:
            str or None: Decoded QR code data if found, otherwise None.
        """
        if frame is None:
            return None

        # Convert to grayscale for better detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Decode QR codes in the frame
        qr_codes = decode(gray)

        if qr_codes:
            for qr in qr_codes:
                data = qr.data.decode("utf-8")
                # Draw rectangle around detected QR code
                points = qr.polygon
                if points is not None and len(points) == 4:
                    pts = [(pt.x, pt.y) for pt in points]
                    cv2.polylines(frame, [np.array(pts, np.int32)], True, (0, 255, 0), 2)
                return data

        return None

    def scan_once(self, timeout=10):
        """
        Scan for a single QR code with a timeout.

        Args:
            timeout (int): Maximum time in seconds to wait for a scan.

        Returns:
            str or None: Decoded QR code data if found within timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            frame = self.read_frame()
            if frame is None:
                continue

            data = self.scan_qr_code(frame)
            if data is not None:
                current_time = time.time()
                # Cooldown to prevent duplicate scans
                if current_time - self.last_scan_time >= self.cooldown:
                    self.last_scanned_data = data
                    self.last_scan_time = current_time
                    return data

        return None

    def scan_continuous(self, callback=None, window_name="QR Code Scanner"):
        """
        Continuously scan QR codes from the webcam, displaying the live feed.

        Args:
            callback (function, optional): Called with decoded data when a QR is detected.
            window_name (str): Name of the OpenCV window.
        """
        self.start()
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        try:
            while True:
                frame = self.read_frame()
                if frame is None:
                    continue

                # Scan for QR codes
                data = self.scan_qr_code(frame)

                # Display status
                if data is not None:
                    current_time = time.time()
                    if current_time - self.last_scan_time >= self.cooldown:
                        self.last_scanned_data = data
                        self.last_scan_time = current_time
                        if callback:
                            callback(data)

                # Show the frame
                cv2.imshow(window_name, frame)

                # Exit on 'q' or 'Q'
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    break
        finally:
            self.stop()
            cv2.destroyAllWindows()


# Lazy import to avoid circular imports
import numpy as np


if __name__ == "__main__":
    # Quick test of the scanner
    scanner = QRScanner()
    print("Scanner initialized. Press 'q' to quit.")
    scanner.scan_continuous()