from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    profile_pic = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    image_url = Column(String, nullable=True)

    # JSON şema alanları (Person 2 - Hafta 1)
    priority = Column(String, default="Normal")        # High | Normal | Low
    status = Column(String, default="In-Progress")     # To-Do | In-Progress | Completed
    deadline = Column(String, nullable=True)            # ISO-8601 (YYYY-MM-DD)
    assigned_to = Column(String, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))

    # CRDT / LWW (Last-Write-Wins) için alan bazlı zaman damgaları
    title_updated_at = Column(Float, default=0.0)
    desc_updated_at = Column(Float, default=0.0)

    # Audit alanları (Person 2 - Hafta 3)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")