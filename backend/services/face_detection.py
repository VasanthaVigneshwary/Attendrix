import cv2
import numpy as np
from typing import List, Tuple
from backend.services.face_utils import detect_face_boxes

def detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect faces in an image with multi-scale Haar cascade and NMS.

    Args:
        image: BGR image as a NumPy array.
    Returns:
        List of bounding boxes (x, y, w, h).
    """
    return detect_face_boxes(image)

