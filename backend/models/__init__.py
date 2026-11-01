from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String)
    year = Column(String)
    section = Column(String)
    embedding = relationship("FaceEmbedding", back_populates="student", uselist=False, cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student")

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    embedding = Column(LargeBinary, nullable=False)  # store np.ndarray.tobytes()
    student = relationship("Student", back_populates="embedding")

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(Integer, primary_key=True)
    session_date = Column(Date, unique=True, nullable=False)
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (UniqueConstraint('session_id', 'student_id', name='_session_student_uc'),)
    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")
