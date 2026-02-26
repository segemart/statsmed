"""
SQLAlchemy models for statsmed: User, DataFile, AnalysisResult.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    data_files = relationship("DataFile", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class DataFile(Base):
    """Uploaded CSV/Excel file metadata; file stored on disk under user dir."""
    __tablename__ = "data_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False, unique=True)  # path on server
    csv_delimiter = Column(String(10), nullable=False, default=",")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="data_files")
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="data_file",
        cascade="all, delete-orphan",
        order_by="AnalysisResult.created_at",
    )

    def __repr__(self):
        return f"<DataFile(id={self.id}, filename='{self.original_filename}')>"


class AnalysisResult(Base):
    """Single analysis run: test id, text output, optional figure (base64)."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    data_file_id = Column(Integer, ForeignKey("data_files.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(String(80), nullable=False)
    label = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    figure_base64 = Column(Text, nullable=True)
    params_json = Column(Text, nullable=True)  # JSON string of params used
    created_at = Column(DateTime, default=datetime.utcnow)

    data_file = relationship("DataFile", back_populates="analysis_results")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, test_id='{self.test_id}')>"
