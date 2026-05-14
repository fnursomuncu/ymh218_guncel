from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Literal
import datetime
import re

from security import is_password_strong, PASSWORD_POLICY_MESSAGE


PriorityLiteral = Literal["High", "Normal", "Low"]
StatusLiteral = Literal["To-Do", "In-Progress", "Completed"]
DEADLINE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", "email", "password", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.fullmatch(USERNAME_PATTERN, v):
            raise ValueError("Kullanıcı adı sadece harf, rakam, nokta, alt çizgi ve kısa çizgi içerebilir.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.fullmatch(EMAIL_PATTERN, v):
            raise ValueError("Geçerli bir e-posta adresi girin.")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not is_password_strong(v):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    profile_pic: Optional[str] = None
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier", "password", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("old_password", "new_password", "confirm_password", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if not is_password_strong(v):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return v


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    task_id: int

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

class CommentResponse(BaseModel):
    id: int
    text: str
    task_id: int
    author_id: int
    model_config = ConfigDict(from_attributes=True)

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)

    priority: Optional[PriorityLiteral] = "Normal"
    status: Optional[StatusLiteral] = "In-Progress"
    deadline: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, max_length=120)

    title_updated_at: float
    desc_updated_at: float

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline(cls, v):
        if v in (None, ""):
            return None
        if not isinstance(v, str) or not re.fullmatch(DEADLINE_PATTERN, v):
            raise ValueError("Son tarih biçimi YYYY-MM-DD olmalıdır.")
        try:
            datetime.date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("Geçerli bir tarih giriniz.") from exc
        return v


class TaskCreate(TaskBase):
    pass


class TaskSync(TaskBase):
    id: int


class TaskResponse(TaskSync):
    image_url: Optional[str] = None
    owner_id: int
    created_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    comments: List['CommentResponse'] = []
    model_config = ConfigDict(from_attributes=True)


class TaskStats(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    overdue: int
    completed_this_week: int


class TaskImportItem(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    priority: Optional[PriorityLiteral] = "Normal"
    status: Optional[StatusLiteral] = "In-Progress"
    deadline: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, max_length=120)


class TaskImportPayload(BaseModel):
    tasks: List[TaskImportItem]