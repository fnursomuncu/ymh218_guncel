from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, Query
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from jose import JWTError, jwt
from pathlib import Path
from uuid import uuid4
import datetime
import io
import shutil
import os
import json

import models
import schemas
import security
from database import engine, get_db, run_lightweight_migrations

ALLOWED_PRIORITIES = {"High", "Normal", "Low"}
ALLOWED_STATUSES = {"To-Do", "In-Progress", "Completed"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

models.Base.metadata.create_all(bind=engine)
run_lightweight_migrations()
app = FastAPI(title="Görev Yöneticisi API")

# Jedan i jedini CORS blok koji ti treba
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
PROFILE_DIR = UPLOAD_DIR / "profiles"
TASK_DIR = UPLOAD_DIR / "tasks"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
TASK_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

FIELD_LABELS = {
    "username": "Kullanıcı adı",
    "email": "E-posta",
    "password": "Şifre",
    "identifier": "Kullanıcı adı/e-posta",
    "old_password": "Eski şifre",
    "new_password": "Yeni şifre",
    "confirm_password": "Şifre tekrarı",
    "title": "Başlık",
    "description": "Açıklama",
    "text": "Yorum",
    "file": "Dosya",
}


def save_upload(upload: UploadFile, target_dir: Path, prefix: str = "") -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix
    filename = f"{prefix}{uuid4().hex}{suffix}"
    file_path = target_dir / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return f"/uploads/{target_dir.name}/{filename}"


def delete_local_file(file_url: str | None):
    if not file_url:
        return
    local_path = file_url.lstrip("/")
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError:
            pass


def translate_validation_error(error: dict) -> str:
    loc = error.get("loc") or []
    field = next((x for x in reversed(loc) if x != "body"), None)
    label = FIELD_LABELS.get(field, "Alan")
    err_type = error.get("type", "")
    ctx = error.get("ctx") or {}

    if err_type == "missing":
        return f"{label} zorunludur."
    if field == "email":
        return "Geçerli bir e-posta adresi girin."
    if field == "identifier":
        if err_type == "string_too_short":
            return "Kullanıcı adı/e-posta en az 3 karakter olmalı."
        return "Kullanıcı adı/e-posta geçersiz."
    if field == "username":
        if err_type == "string_too_short":
            return f"Kullanıcı adı en az {ctx.get('min_length', 3)} karakter olmalı."
        if err_type == "string_too_long":
            return f"Kullanıcı adı en fazla {ctx.get('max_length', 30)} karakter olabilir."
        return "Kullanıcı adı geçersiz."
    if field in {"password", "new_password"}:
        return security.PASSWORD_POLICY_MESSAGE
    if field in {"old_password", "confirm_password"}:
        if err_type == "string_too_short":
            return f"{label} en az {ctx.get('min_length', 1)} karakter olmalı."
        return f"{label} geçersiz."
    if field == "title":
        if err_type == "string_too_short":
            return "Başlık boş olamaz."
        return "Başlık geçersiz."
    return error.get("msg", "Gönderilen veriler geçersiz.")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        msg = translate_validation_error(error)
        if msg not in messages:
            messages.append(msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": " ".join(messages)},
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum süresi doldu, lütfen tekrar giriş yapın.",
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# ///// WebSocket /////
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # İstemciden veri geldiğinde (örneğin bir task güncellendiğinde) bunu dinle
            data = await websocket.receive_text()
            
            # Gelen veriyi güvenli bir şekilde JSON formatına çevir
            try:
                parsed_data = json.loads(data)
                # Gelen değişikliği diğer tüm aktif bağlantılara ilet
                await manager.broadcast({"type": "update", "payload": parsed_data})
            except json.JSONDecodeError:
                 pass # Gelen veri JSON değilse yoksay
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    username = user.username.strip()
    email = user.email.strip().lower()

    existing_user = db.query(models.User).filter(
        (models.User.username == username) | (func.lower(models.User.email) == email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kullanıcı adı veya e-posta zaten kullanımda."
        )

    hashed_pw = security.get_password_hash(user.password)
    new_user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    identifier = user_data.identifier.strip()
    email_like = identifier.lower()

    user = db.query(models.User).filter(
        (models.User.username == identifier) | (func.lower(models.User.email) == email_like)
    ).first()

    if not user or not security.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı/e-posta veya şifre hatalı."
        )

    token = security.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/users/me/profile-pic")
def upload_profile_pic(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Sadece görsel dosyaları yükleyebilirsiniz.")

    if current_user.profile_pic:
        delete_local_file(current_user.profile_pic)

    image_url = save_upload(file, PROFILE_DIR, prefix=f"profile_{current_user.id}_")
    current_user.profile_pic = image_url
    db.commit()

    return {"path": image_url, "msg": "Profil fotoğrafı yüklendi."}


@app.delete("/users/me/profile-pic")
def delete_profile_pic(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    delete_local_file(current_user.profile_pic)
    current_user.profile_pic = None
    db.commit()
    return {"msg": "Profil fotoğrafı kaldırıldı."}


@app.post("/users/me/change-password")
def change_password(
    data: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not security.verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Eski şifre hatalı.")

    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Yeni şifreler eşleşmiyor.")

    if not security.is_password_strong(data.new_password):
        raise HTTPException(status_code=400, detail=security.PASSWORD_POLICY_MESSAGE)

    current_user.hashed_password = security.get_password_hash(data.new_password)
    db.commit()
    return {"msg": "Şifre başarıyla güncellendi."}


def _validate_priority(value: str) -> str:
    if value not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"Geçersiz öncelik. İzin verilenler: {sorted(ALLOWED_PRIORITIES)}")
    return value


def _validate_status(value: str) -> str:
    if value not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail=f"Geçersiz durum. İzin verilenler: {sorted(ALLOWED_STATUSES)}")
    return value


def _validate_deadline(value: str | None) -> str | None:
    if not value:
        return None
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail="Son tarih biçimi YYYY-MM-DD olmalıdır.")
    return value


@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_tasks(
    priority: str | None = Query(default=None),
    status: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Başlık/açıklama içinde arama"),
    sort: str = Query(default="-id", description="id, -id, deadline, -deadline, priority"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Task).filter(models.Task.owner_id == current_user.id)

    if priority:
        _validate_priority(priority)
        query = query.filter(models.Task.priority == priority)
    if status:
        _validate_status(status)
        query = query.filter(models.Task.status == status)
    if assigned_to:
        query = query.filter(models.Task.assigned_to == assigned_to.strip())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(models.Task.title.ilike(like), models.Task.description.ilike(like)))

    sort_map = {
        "id": models.Task.id.asc(),
        "-id": models.Task.id.desc(),
        "deadline": models.Task.deadline.asc(),
        "-deadline": models.Task.deadline.desc(),
        "priority": models.Task.priority.asc(),
        "-priority": models.Task.priority.desc(),
    }
    query = query.order_by(sort_map.get(sort, models.Task.id.desc()))
    return query.all()


@app.get("/tasks/stats", response_model=schemas.TaskStats)
def get_task_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    base = db.query(models.Task).filter(models.Task.owner_id == current_user.id)
    total = base.count()

    by_status = {s: 0 for s in ALLOWED_STATUSES}
    for st, cnt in (
        base.with_entities(models.Task.status, func.count(models.Task.id))
        .group_by(models.Task.status).all()
    ):
        if st in by_status:
            by_status[st] = cnt

    by_priority = {p: 0 for p in ALLOWED_PRIORITIES}
    for pr, cnt in (
        base.with_entities(models.Task.priority, func.count(models.Task.id))
        .group_by(models.Task.priority).all()
    ):
        if pr in by_priority:
            by_priority[pr] = cnt

    today = datetime.date.today().isoformat()
    overdue = base.filter(
        models.Task.deadline.isnot(None),
        models.Task.deadline < today,
        models.Task.status != "Completed",
    ).count()

    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    completed_this_week = base.filter(
        models.Task.status == "Completed",
        models.Task.completed_at.isnot(None),
        models.Task.completed_at >= week_ago,
    ).count()

    return schemas.TaskStats(
        total=total,
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        completed_this_week=completed_this_week,
    )


@app.get("/tasks/export")
def export_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tasks = db.query(models.Task).filter(models.Task.owner_id == current_user.id).all()
    payload = {
        "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
        "owner": current_user.username,
        "schema": "task_schema.json",
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "deadline": t.deadline,
                "assigned_to": t.assigned_to,
                "image_url": t.image_url,
                "owner_id": t.owner_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "title_updated_at": t.title_updated_at,
                "desc_updated_at": t.desc_updated_at,
            }
            for t in tasks
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    headers = {"Content-Disposition": 'attachment; filename="tasks-export.json"'}
    return StreamingResponse(io.BytesIO(body), media_type="application/json", headers=headers)


@app.post("/tasks/import")
def import_tasks(
    payload: schemas.TaskImportPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.datetime.utcnow().timestamp()
    created = 0
    for item in payload.tasks:
        deadline = _validate_deadline(item.deadline)
        task = models.Task(
            title=item.title.strip(),
            description=item.description.strip(),
            priority=item.priority or "Normal",
            status=item.status or "In-Progress",
            deadline=deadline,
            assigned_to=item.assigned_to.strip() if item.assigned_to else None,
            owner_id=current_user.id,
            title_updated_at=now,
            desc_updated_at=now,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(task)
        created += 1
    db.commit()
    return {"created": created}


@app.post("/tasks", response_model=schemas.TaskResponse)
def create_task(
    title: str = Form(...),
    description: str = Form(...),
    priority: str = Form("Normal"),
    status: str = Form("In-Progress"),
    deadline: str = Form(""),
    assigned_to: str = Form(""),
    title_at: float = Form(...),
    desc_at: float = Form(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_priority(priority)
    _validate_status(status)
    deadline_value = _validate_deadline(deadline if deadline else None)

    image_url = None
    if file and file.filename:
        image_url = save_upload(file, TASK_DIR, prefix=f"task_{current_user.id}_")

    new_task = models.Task(
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        status=status,
        deadline=deadline_value,
        assigned_to=assigned_to.strip() if assigned_to else None,
        title_updated_at=title_at,
        desc_updated_at=desc_at,
        image_url=image_url,
        owner_id=current_user.id,
        created_at=datetime.datetime.utcnow(),
        completed_at=datetime.datetime.utcnow() if status == "Completed" else None,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.post("/tasks/{task_id}/complete", response_model=schemas.TaskResponse)
def mark_task_complete(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id, models.Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    task.status = "Completed"
    task.completed_at = datetime.datetime.utcnow()
    task.title_updated_at = datetime.datetime.utcnow().timestamp()
    db.commit()
    db.refresh(task)
    return task


@app.post("/tasks/{task_id}/reopen", response_model=schemas.TaskResponse)
def reopen_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == task_id, models.Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    task.status = "In-Progress"
    task.completed_at = None
    task.title_updated_at = datetime.datetime.utcnow().timestamp()
    db.commit()
    db.refresh(task)
    return task

@app.post("/tasks/sync", response_model=schemas.TaskResponse)
def sync_task(incoming: schemas.TaskSync, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_task = db.query(models.Task).filter(
        models.Task.id == incoming.id, models.Task.owner_id == current_user.id
    ).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    if incoming.priority is not None:
        _validate_priority(incoming.priority)
    if incoming.status is not None:
        _validate_status(incoming.status)
    incoming_deadline = _validate_deadline(incoming.deadline)

    # Alan bazlı LWW (Last-Write-Wins) çakışma yönetimi
    updated = False
    if incoming.title_updated_at > db_task.title_updated_at:
        previous_status = db_task.status
        db_task.title = incoming.title
        db_task.title_updated_at = incoming.title_updated_at
        db_task.priority = incoming.priority or db_task.priority
        db_task.status = incoming.status or db_task.status
        db_task.deadline = incoming_deadline
        db_task.assigned_to = incoming.assigned_to
        if db_task.status == "Completed" and previous_status != "Completed":
            db_task.completed_at = datetime.datetime.utcnow()
        elif db_task.status != "Completed":
            db_task.completed_at = None
        updated = True

    if incoming.desc_updated_at > db_task.desc_updated_at:
        db_task.description = incoming.description
        db_task.desc_updated_at = incoming.desc_updated_at
        updated = True

    if updated:
        db.commit()
        db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Yetkisiz işlem.")

    delete_local_file(task.image_url)
    db.delete(task)
    db.commit()
    return {"msg": "Görev silindi."}


@app.post("/comments", response_model=schemas.CommentResponse)
def add_comment(
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(
        models.Task.id == comment.task_id,
        models.Task.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    comment_text = comment.text.strip()
    if not comment_text:
        raise HTTPException(status_code=400, detail="Yorum boş olamaz.")

    new_comment = models.Comment(
        text=comment_text,
        task_id=comment.task_id,
        author_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment