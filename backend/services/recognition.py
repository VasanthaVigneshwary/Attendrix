"""
Face recognition service.
- Accepts a classroom image (potentially multiple faces)
- Detects all faces using Haar cascade
- Generates FaceNet embedding for each detected face
- Compares against all stored student embeddings using cosine distance
- Returns recognized students and unknown faces
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Student, FaceEmbedding
from backend.services.face_utils import (
    decode_image, detect_face_boxes,
    generate_embedding, cosine_distance, embedding_from_bytes,
    THRESHOLD
)


def recognize_faces_in_image(image_bytes: bytes, db: Session) -> Dict[str, Any]:
    """
    Detect and recognize all faces in a classroom image.

    Returns:
        {
          "total_faces_detected": int,
          "recognized": [{"student_id", "name", "department", "year", "section", "confidence", "box"}, ...],
          "unknown": [{"box": [x,y,w,h]}, ...],
          "error": str | None
        }
    """
    # Decode image
    try:
        img = decode_image(image_bytes)
    except ValueError as e:
        return {"total_faces_detected": 0, "recognized": [], "unknown": [], "error": str(e)}

    # Detect all faces
    boxes = detect_face_boxes(img)
    if len(boxes) == 0:
        return {
            "total_faces_detected": 0,
            "recognized": [],
            "unknown": [],
            "error": "No faces detected in the image."
        }

    # Load all stored embeddings once
    embeddings_db = (
        db.query(FaceEmbedding)
        .join(Student, FaceEmbedding.student_id == Student.id)
        .all()
    )

    recognized = []
    unknown = []

    for box in boxes:
        x, y, w, h = box
        face_crop = img[y:y+h, x:x+w]

        # Generate embedding for this face
        try:
            query_emb = generate_embedding(face_crop)
        except Exception:
            unknown.append({"box": box})
            continue

        # Compare with every stored embedding
        best_distance = float("inf")
        best_student = None

        for emb_record in embeddings_db:
            stored_emb = embedding_from_bytes(emb_record.embedding)
            dist = cosine_distance(query_emb, stored_emb)
            if dist < best_distance:
                best_distance = dist
                best_student = emb_record.student

        if best_student is not None and best_distance <= THRESHOLD:
            recognized.append({
                "student_id": best_student.student_id,
                "name": best_student.name,
                "department": best_student.department,
                "year": best_student.year,
                "section": best_student.section,
                "distance": round(best_distance, 4),
                "confidence": round(max(0, 1.0 - best_distance / THRESHOLD), 4),
                "box": box,
            })
        else:
            unknown.append({"box": box, "nearest_distance": round(best_distance, 4) if best_student else None})

    return {
        "total_faces_detected": len(boxes),
        "recognized": recognized,
        "unknown": unknown,
        "error": None,
    }

