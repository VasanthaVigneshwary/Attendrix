import io
import csv
from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import SessionLocal
from backend.services.recognition import recognize_faces_in_image
from backend.services.attendance_service import (
    mark_attendance, get_attendance_records, get_daily_summary
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/recognize")
async def recognize_and_mark(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a classroom image.
    - Detect all faces
    - Recognize registered students
    - Mark attendance for recognized students
    - Return full recognition result + attendance marking status
    """
    image_bytes = await image.read()

    # Face recognition
    recognition_result = recognize_faces_in_image(image_bytes, db)

    # Mark attendance for recognized students only
    attendance_results = []
    if recognition_result["recognized"]:
        attendance_results = mark_attendance(db, recognition_result["recognized"])

    return {
        "recognition": recognition_result,
        "attendance": attendance_results,
    }


@router.get("/records")
def get_records(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by student name or ID"),
    db: Session = Depends(get_db),
):
    """Return attendance records with optional filtering."""
    return get_attendance_records(db, date_str=date, search=search)


@router.get("/summary")
def attendance_summary(
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return daily attendance summary (present/absent/percentage)."""
    return get_daily_summary(db, date_str=date)


@router.get("/export")
def export_csv(
    date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export attendance records as a CSV file."""
    records = get_attendance_records(db, date_str=date, search=search)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["student_id", "name", "department", "year", "section", "date", "time"],
    )
    writer.writeheader()
    for r in records:
        writer.writerow({k: r.get(k, "") for k in writer.fieldnames})

    output.seek(0)
    filename = f"attendance_{date or 'all'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

