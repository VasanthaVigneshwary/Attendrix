from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import SessionLocal
from backend.services.registration import register_student as _register
from backend.models import Student

router = APIRouter(prefix="/students", tags=["Students"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def create_student(
    student_id: str = Form(...),
    name: str = Form(...),
    department: str = Form(""),
    year: str = Form(""),
    section: str = Form(""),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Register a new student with face image."""
    return _register(db, student_id, name, department, year, section, image)


@router.get("/")
def list_students(db: Session = Depends(get_db)):
    """Return all registered students."""
    students = db.query(Student).all()
    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "name": s.name,
            "department": s.department,
            "year": s.year,
            "section": s.section,
        }
        for s in students
    ]


@router.delete("/{student_db_id}")
def delete_student(student_db_id: int, db: Session = Depends(get_db)):
    """Delete a student record (cascades to embeddings and attendance)."""
    student = db.query(Student).filter(Student.id == student_db_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    db.delete(student)
    db.commit()
    return {"detail": f"Student '{student.name}' deleted successfully."}
