import os
import numpy as np
import cv2
from typing import Optional, List
from deepface import DeepFace

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MODEL_NAME = "Facenet"   # 128-dim embeddings
THRESHOLD = 0.40         # Cosine similarity threshold (tuned for FaceNet 128-dim)
                         # Embeddings closer than THRESHOLD are considered a match.
                         # Cosine similarity range: 0 (identical) to 2 (opposite).
                         # 0.40 empirically balances recall and precision for FaceNet.

# ─────────────────────────────────────────────────────────────────────────────
# Haar cascade for fast multi-face detection
# ─────────────────────────────────────────────────────────────────────────────
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_CASCADE = cv2.CascadeClassifier(_CASCADE_PATH)


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes to a BGR NumPy array."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image. Ensure the file is a valid image (JPG, PNG).")
    return img


def non_max_suppression(boxes: List[List[int]], overlap_thresh: float = 0.3) -> List[List[int]]:
    """Suppresses heavily overlapping bounding boxes from multi-scale Haar detections."""
    if len(boxes) == 0:
        return []
    box_arr = np.array(boxes, dtype=float)
    x1 = box_arr[:, 0]
    y1 = box_arr[:, 1]
    x2 = box_arr[:, 0] + box_arr[:, 2]
    y2 = box_arr[:, 1] + box_arr[:, 3]
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)
    pick = []
    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:last]]
        idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
    return box_arr[pick].astype(int).tolist()


def detect_face_boxes(img: np.ndarray) -> List[List[int]]:
    """Detect face bounding boxes using Haar cascade with NMS.
    Returns a list of [x, y, w, h] boxes.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _CASCADE.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    if len(faces) == 0:
        return []
    return non_max_suppression(faces.tolist(), overlap_thresh=0.3)


def generate_embedding(face_img: np.ndarray) -> np.ndarray:
    """Generate a FaceNet 128-dim embedding from a face image (BGR NumPy array).
    Uses DeepFace with enforce_detection=False because we've already cropped the face.
    """
    # Convert BGR -> RGB (DeepFace expects RGB)
    face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    result = DeepFace.represent(
        img_path=face_rgb,
        model_name=MODEL_NAME,
        enforce_detection=False,
        detector_backend="skip",   # we already cropped — skip internal detection
    )
    return np.array(result[0]["embedding"], dtype=np.float32)


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance between two embedding vectors.
    Returns 0 for identical vectors, up to 2 for opposite vectors.
    """
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 2.0   # maximum distance
    return float(1.0 - np.dot(a, b) / (a_norm * b_norm))


def embedding_from_bytes(blob: bytes) -> np.ndarray:
    """Reconstruct a float32 numpy array from a stored byte blob."""
    return np.frombuffer(blob, dtype=np.float32).copy()

