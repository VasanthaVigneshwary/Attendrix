from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Student
from backend.services.attendance_service import get_daily_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """Return dashboard overview stats."""
    summary = get_daily_summary(db)
    summary["total_registered"] = db.query(Student).count()
    return summary

