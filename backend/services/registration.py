"""
Student registration service.
- Validates image
- Detects exactly one face (registration requires a clear solo portrait)
- Generates FaceNet embedding using face_utils
- Stores student + embedding in SQLite
- Prevents duplicate student IDs
"""
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.models import Student, FaceEmbedding
from backend.services.face_utils import decode_image, detect_face_boxes, generate_embedding


def register_student(
    db: Session,
    student_id: str,
    name: str,
    department: str,
    year: str,
    section: str,
    image: UploadFile,
) -> dict:
    """Register a new student with their face embedding."""
    # 1. Duplicate ID check
    existing = db.query(Student).filter(Student.student_id == student_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Student ID '{student_id}' is already registered.")

    # 2. Validate and decode image
    image_bytes = image.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file.")
    try:
        img = decode_image(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Detect face(s)
    boxes = detect_face_boxes(img)
    if len(boxes) == 0:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the image. Please upload a clear, well-lit portrait photo."
        )
    if len(boxes) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"{len(boxes)} faces detected. Registration requires a single-face portrait."
        )

    # 4. Crop face and generate embedding
    x, y, w, h = boxes[0]
    face_crop = img[y:y+h, x:x+w]
    try:
        embedding_vec = generate_embedding(face_crop)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

    # 5. Persist to database
    new_student = Student(
        student_id=student_id,
        name=name,
        department=department,
        year=year,
        section=section,
    )
    db.add(new_student)
    db.flush()   # get auto-generated primary key

    emb_record = FaceEmbedding(
        student_id=new_student.id,
        embedding=embedding_vec.tobytes(),
    )
    db.add(emb_record)
    db.commit()
    db.refresh(new_student)

    return {
        "id": new_student.id,
        "student_id": new_student.student_id,
        "name": new_student.name,
        "department": new_student.department,
        "year": new_student.year,
        "section": new_student.section,
        "message": "Student registered successfully.",
    }
