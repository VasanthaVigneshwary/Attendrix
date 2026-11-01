"""
Attendance service.
- Gets or creates today's session
- Marks recognized students as Present
- Prevents duplicate entries (unique constraint in DB + pre-check)
- Returns per-student mark result
"""
import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models import Student, AttendanceSession, AttendanceRecord


def get_or_create_session(db: Session, date: datetime.date = None) -> AttendanceSession:
    """Get today's session or create a new one."""
    if date is None:
        date = datetime.date.today()
    session_rec = db.query(AttendanceSession).filter(AttendanceSession.session_date == date).first()
    if not session_rec:
        session_rec = AttendanceSession(session_date=date)
        db.add(session_rec)
        db.commit()
        db.refresh(session_rec)
    return session_rec


def mark_attendance(db: Session, recognized_students: List[Dict]) -> List[Dict[str, Any]]:
    """
    Mark attendance for recognized students.

    Args:
        recognized_students: List of dicts with 'student_id' (the string ID like 'S001')
    Returns:
        List of results per student with status (marked / already_marked / not_found)
    """
    results = []
    session_rec = get_or_create_session(db)
    today = datetime.date.today()

    # Collect unique student_ids (avoid marking same student twice in one call)
    seen = set()
    for s in recognized_students:
        sid = s.get("student_id")
        if sid in seen:
            continue
        seen.add(sid)

        student = db.query(Student).filter(Student.student_id == sid).first()
        if not student:
            results.append({"student_id": sid, "status": "not_found"})
            continue

        # Check if already marked for today's session
        existing = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session_rec.id,
                AttendanceRecord.student_id == student.id,
            )
            .first()
        )
        if existing:
            results.append({
                "student_id": sid,
                "name": student.name,
                "status": "already_marked",
                "timestamp": existing.timestamp.isoformat(),
            })
            continue

        # Mark as present
        try:
            record = AttendanceRecord(
                session_id=session_rec.id,
                student_id=student.id,
                timestamp=datetime.datetime.now(),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            results.append({
                "student_id": sid,
                "name": student.name,
                "status": "marked",
                "timestamp": record.timestamp.isoformat(),
            })
        except IntegrityError:
            db.rollback()
            results.append({"student_id": sid, "name": student.name, "status": "already_marked"})

    return results


def get_attendance_records(
    db: Session,
    date_str: str = None,
    search: str = None,
) -> List[Dict[str, Any]]:
    """Query attendance records with optional date filter and name/ID search."""
    query = (
        db.query(AttendanceRecord, Student, AttendanceSession)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
    )
    if date_str:
        try:
            d = datetime.date.fromisoformat(date_str)
            query = query.filter(AttendanceSession.session_date == d)
        except ValueError:
            pass
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            (Student.name.ilike(search_lower)) | (Student.student_id.ilike(search_lower))
        )
    rows = query.order_by(AttendanceRecord.timestamp.desc()).all()
    records = []
    for rec, stu, sess in rows:
        records.append({
            "id": rec.id,
            "student_id": stu.student_id,
            "name": stu.name,
            "department": stu.department,
            "year": stu.year,
            "section": stu.section,
            "date": sess.session_date.isoformat(),
            "time": rec.timestamp.strftime("%H:%M:%S"),
            "timestamp": rec.timestamp.isoformat(),
        })
    return records


def get_daily_summary(db: Session, date_str: str = None) -> Dict[str, Any]:
    """Return present/absent counts and percentage for a given date (default: today)."""
    if date_str:
        try:
            date = datetime.date.fromisoformat(date_str)
        except ValueError:
            date = datetime.date.today()
    else:
        date = datetime.date.today()

    total_students = db.query(Student).count()
    session_rec = db.query(AttendanceSession).filter(AttendanceSession.session_date == date).first()
    present_count = 0
    if session_rec:
        present_count = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.session_id == session_rec.id)
            .count()
        )
    absent_count = max(0, total_students - present_count)
    pct = round((present_count / total_students * 100), 1) if total_students > 0 else 0.0
    return {
        "date": date.isoformat(),
        "total_students": total_students,
        "present": present_count,
        "absent": absent_count,
        "attendance_percentage": pct,
    }

