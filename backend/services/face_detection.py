import cv2
import numpy as np
from typing import List, Tuple

# Load OpenCV's pre-trained Haar cascade for frontal face detection
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect faces in an image.

    Args:
        image: BGR image as a NumPy array.
    Returns:
        List of bounding boxes (x, y, w, h).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return faces.tolist()
