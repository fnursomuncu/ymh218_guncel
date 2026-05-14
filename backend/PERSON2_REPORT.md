# تقرير شامل ومفصّل لكل ما أُضيف على مشروع Görev Yöneticisi

> الدور: **Person 2 — Task & Data** | الأسابيع: 1 → 4 | حالة الاختبارات: **14/14 ✅** و **E2E ✅**

---

## 1) نظرة عامة على التغييرات

### الملفات الجديدة (6 ملفات)

| # | الملف | الغرض |
|---|------|--------|
| 1 | `backend/task_schema.json` | تعريف JSON Schema رسمي (Draft-07) لبنية المهمة |
| 2 | `backend/tests/__init__.py` | تحويل مجلد الاختبارات لحزمة Python |
| 3 | `backend/tests/conftest.py` | Fixtures مشتركة لاختبارات pytest |
| 4 | `backend/tests/test_tasks.py` | 14 اختبار لتناسق البيانات |
| 5 | `backend/e2e_test.py` | سكريبت محاكاة سيناريو End-to-End كامل |
| 6 | `backend/WORKFLOW.md` | توثيق سير العمل والـ workflow diagram |

### الملفات المُعدَّلة (7 ملفات)

| # | الملف | نوع التعديل |
|---|------|--------------|
| 1 | `backend/models.py` | إضافة أعمدة `created_at`، `completed_at` |
| 2 | `backend/schemas.py` | Enums + Validators + Stats/Import schemas |
| 3 | `backend/database.py` | دعم `DATABASE_URL` + migration تلقائي للأعمدة |
| 4 | `backend/main.py` | 6 endpoints جديدة + فلترة + validators |
| 5 | `backend/requirements.txt` | إضافة `pytest`, `httpx`, `requests` |
| 6 | `frontend/src/App.jsx` | شريط أدوات + Kanban + إحصائيات + Reopen + Export/Import |
| 7 | `frontend/src/App.css` | أنماط الـ stats-bar، toolbar، kanban-board |

---

## 2) الأسبوع الأول — Initialization & Basic Structure

### 2.1 ملف `backend/task_schema.json` (جديد)

ملف JSON Schema رسمي بمعيار **Draft-07** لتوثيق بنية كائن `Task`. يفيد كـ"عقد بيانات" (data contract) لأي نظام خارجي يتعامل مع المشروع.

**أبرز محتوياته**:
- `$schema` و`$id` رسميان للتعرّف على الإصدار.
- 12 حقل موثَّق (id، title، description، priority، status، deadline، assigned_to، image_url، owner_id، created_at، completed_at، title_updated_at، desc_updated_at، comments).
- enums صريحة:
  - `priority`: `["High", "Normal", "Low"]`
  - `status`: `["To-Do", "In-Progress", "Completed"]`
- صيغ (formats):
  - `deadline`: `format: "date"` (YYYY-MM-DD)
  - `created_at` و`completed_at`: `format: "date-time"` (ISO-8601)
- قواعد طول النص (`maxLength: 120` للعنوان، `2000` للوصف، `500` للتعليق).
- `additionalProperties: false` لمنع الحقول غير المتوقعة.
- مخطط فرعي للتعليقات (comments) بداخل كل مهمة.

### 2.2 تعديلات `backend/models.py`

**قبل**: نموذج `Task` لم يكن يحتوي حقول لتتبع تاريخ الإنشاء أو وقت الإكمال.

**بعد**:
- أُضيف العمود **`created_at = Column(DateTime, default=datetime.datetime.utcnow)`** ليُسجَّل تلقائياً وقت إنشاء كل مهمة.
- أُضيف العمود **`completed_at = Column(DateTime, nullable=True)`** ليُحدَّد فقط عند الانتقال إلى حالة `Completed`.
- أُعيد تنظيم التعليقات وتجميع الحقول منطقياً (CRUD، JSON Schema، CRDT/LWW، Audit).

### 2.3 تعديلات `backend/database.py`

**التغييرات الجوهرية**:

1. **دعم متغير بيئي للاختبار**:
   ```python
   SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
   ```
   هذا يسمح للـ pytest باستخدام قاعدة بيانات معزولة في `tmp_path` لكل تشغيل.

2. **`run_lightweight_migrations()`** — دالة migration يدوية بسيطة:
   - تستخدم `inspect(engine)` لقراءة أعمدة جدول `tasks` الحالية.
   - إذا كان أحد الأعمدة الجديدة مفقوداً، تُنفّذ `ALTER TABLE` عبر قاموس DDL:
     ```python
     _TASK_COLUMN_DDL = {
       "priority":         "ALTER TABLE tasks ADD COLUMN priority VARCHAR DEFAULT 'Normal'",
       "status":           "ALTER TABLE tasks ADD COLUMN status VARCHAR DEFAULT 'In-Progress'",
       "deadline":         "ALTER TABLE tasks ADD COLUMN deadline VARCHAR",
       "assigned_to":      "ALTER TABLE tasks ADD COLUMN assigned_to VARCHAR",
       "title_updated_at": "ALTER TABLE tasks ADD COLUMN title_updated_at FLOAT DEFAULT 0.0",
       "desc_updated_at":  "ALTER TABLE tasks ADD COLUMN desc_updated_at FLOAT DEFAULT 0.0",
       "created_at":       "ALTER TABLE tasks ADD COLUMN created_at DATETIME",
       "completed_at":     "ALTER TABLE tasks ADD COLUMN completed_at DATETIME",
     }
     ```
   - الفائدة: قاعدة بيانات `test.db` الموجودة لم تُحذف، والبيانات القديمة بقيت سليمة، وأُضيفت الأعمدة الجديدة دون تدخل يدوي.

3. تم استدعاء `run_lightweight_migrations()` في `main.py` مباشرة بعد `Base.metadata.create_all(...)`.

### 2.4 تعديلات `backend/schemas.py`

**أ. ثوابت جديدة في الأعلى**:
```python
PriorityLiteral = Literal["High", "Normal", "Low"]
StatusLiteral   = Literal["To-Do", "In-Progress", "Completed"]
DEADLINE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
```
استخدام `Literal` يجعل Pydantic ترفض أي قيمة خارج المجموعة بـ HTTP 422 تلقائياً.

**ب. تحديث `TaskBase`**:
- `priority` و`status` أصبحا من نوع Literal بدل `Optional[str]`.
- `assigned_to` أصبح محدوداً بـ `max_length=120`.
- إضافة `field_validator("deadline")` يتحقّق:
  1. أن السلسلة مطابقة للنمط `YYYY-MM-DD`.
  2. أنها تاريخ صالح فعلاً (`datetime.date.fromisoformat`).

**ج. تحديث `TaskResponse`**: أُضيف الحقلان `created_at: Optional[datetime]` و `completed_at: Optional[datetime]`.

**د. مخططات جديدة للأسبوع 2 و3**:
- **`TaskStats`** ← يُستعمل من قِبَل `/tasks/stats` ويُعرّف:
  - `total: int`
  - `by_status: dict`
  - `by_priority: dict`
  - `overdue: int`
  - `completed_this_week: int`

- **`TaskImportItem`** و **`TaskImportPayload`** ← يستخدمان من قِبَل `/tasks/import` لتحقّق صارم من بنية ملف JSON المستورد:
  ```python
  class TaskImportPayload(BaseModel):
      tasks: List[TaskImportItem]
  ```

---

## 3) الأسبوع الثاني — Development & Interface

### 3.1 تعديلات `backend/main.py` (الجزء الأول: تحضير عام)

**أ. استيرادات جديدة**:
- `Query` من fastapi لاستقبال query params مع validation.
- `StreamingResponse` لإرجاع ملف JSON قابل للتنزيل.
- `or_` من sqlalchemy لبحث متعدد الحقول.
- `datetime` و `io` لتنسيق التاريخ وتدفق الملفات.

**ب. مجموعتان ثابتتان**:
```python
ALLOWED_PRIORITIES = {"High", "Normal", "Low"}
ALLOWED_STATUSES   = {"To-Do", "In-Progress", "Completed"}
```

**ج. ثلاث دوال validation داخلية**:
- `_validate_priority(value)` ← ترفع 422 إذا كان خارج المجموعة.
- `_validate_status(value)` ← مماثلة.
- `_validate_deadline(value)` ← تتحقّق من صيغة `YYYY-MM-DD` وصلاحية التاريخ.

**د. استدعاء migrations** في startup:
```python
models.Base.metadata.create_all(bind=engine)
run_lightweight_migrations()
```

### 3.2 تطوير `GET /tasks` لدعم الفلترة الكاملة

```python
@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_tasks(
    priority: str | None = Query(default=None),
    status:   str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    q: str | None = Query(default=None, description="..."),
    sort: str = Query(default="-id", description="id, -id, deadline, -deadline, priority"),
    ...
):
```

**القدرات الجديدة**:
1. فلتر `?priority=High` (مع validation).
2. فلتر `?status=Completed`.
3. فلتر `?assigned_to=Ahmed`.
4. **بحث حر** `?q=رقم` يبحث في `title` أو `description` بـ `ILIKE` (case-insensitive).
5. **ترتيب** عبر `?sort=...` ضمن قائمة بيضاء (`id`, `-id`, `deadline`, `-deadline`, `priority`, `-priority`).
6. كل العمليات مقيّدة على `owner_id == current_user.id` (لا يرى المستخدم مهام غيره).

### 3.3 endpoint جديد: `GET /tasks/stats`

يحسب 5 مقاييس فورية ويُرجعها بنموذج `TaskStats`:

| الحقل | كيف يُحسب |
|------|-----------|
| `total` | `count()` لكل مهام المستخدم |
| `by_status` | `GROUP BY status` (يبدأ من 0 لكل قيمة لتجنّب المفاتيح الناقصة) |
| `by_priority` | `GROUP BY priority` |
| `overdue` | المهام التي `deadline < today` و `status != 'Completed'` |
| `completed_this_week` | `status='Completed'` و `completed_at >= now - 7 days` |

### 3.4 تحديث `POST /tasks` (إنشاء مهمة)

التحسينات:
- استدعاء `_validate_priority`, `_validate_status`, `_validate_deadline` قبل أي حفظ.
- ضبط `created_at = datetime.utcnow()` تلقائياً.
- ضبط `completed_at` فوراً إذا أُنشئت المهمة بحالة `Completed`.

### 3.5 تحديثات الواجهة الأمامية `frontend/src/App.jsx`

**أ. متغيرات حالة جديدة (state)**:
```jsx
const [taskStatus,      setTaskStatus]      = useState('To-Do');
const [filterPriority,  setFilterPriority]  = useState('All');
const [filterStatus,    setFilterStatus]    = useState('All');
const [searchQuery,     setSearchQuery]     = useState('');
const [stats,           setStats]           = useState(null);
const [editStatus,      setEditStatus]      = useState('In-Progress');
const importFileRef = useRef(null);
```

**ب. دالة `fetchStats()`** تجلب `/tasks/stats` وتحدّث الحالة.

**ج. تحديث `fetchAll()`** ليجلب الإحصائيات بالتوازي مع المهام والمستخدم.

**د. منطق التصفية في الواجهة (مرشّح ثانٍ بعد جلب البيانات)**:
```jsx
const filteredTasks = tasksList.filter((t) => {
  if (filterPriority !== 'All' && t.priority !== filterPriority) return false;
  if (filterStatus   !== 'All' && t.status   !== filterStatus)   return false;
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    const inText = (t.title || '').toLowerCase().includes(q)
                || (t.description || '').toLowerCase().includes(q);
    const inAssignee = (t.assigned_to || '').toLowerCase().includes(q);
    if (!inText && !inAssignee) return false;
  }
  return true;
});
```

**هـ. تجميع المهام حسب الحالة لـ Kanban**:
```jsx
const tasksByStatus = {
  'To-Do':       filteredTasks.filter(t => t.status === 'To-Do'),
  'In-Progress': filteredTasks.filter(t => t.status === 'In-Progress' || !t.status),
  'Completed':   filteredTasks.filter(t => t.status === 'Completed'),
};
```

**و. شريط الإحصائيات (Stats Bar)** — 6 بطاقات أرقام فورية:
- Total · To-Do · In-Progress · Completed · Süresi Geçti (overdue) · Bu Hafta ✓.

**ز. شريط الأدوات (Toolbar)** فوق Kanban:
- Input بحث.
- Select فلتر أولوية (`High/Normal/Low/All`).
- Select فلتر حالة (`To-Do/In-Progress/Completed/All`).
- زر **Export** يستدعي `handleExportTasks()`.
- زر **Import** يفتح `importFileRef.current.click()`.
- input مخفي من نوع file يستدعي `handleImportTasks(e)`.

**ح. لوحة Kanban (3 أعمدة)**:
- كل عمود هو `<div className="kanban-column kanban-todo|kanban-prog|kanban-done">`.
- header العمود يحتوي اسم العمود وعدّاد المهام داخله.
- إذا فارغ يعرض "Görev yok"، وإلا يعرض كل بطاقة مهمة كاملة.

**ط. ميزات إضافية على بطاقة المهمة**:
- عرض `completed_at` كنص "✅ Bitiş: ...".
- بادج (badge) جديد للحالة `To-Do` بلون `status-todo` (أزرق فاتح).
- زر **"↩ Yeniden Aç"** للمهام المكتملة بدلاً من زر التمام.
- إضافة select للحالة في وضع التعديل.

### 3.6 أنماط CSS الجديدة في `App.css`

أُضيفت بلوكات تحت تعليق `/* --- Person 2 / Week 2: filters, stats and Kanban board --- */`:

- `.stats-bar` — flexbox أفقي مع gap.
- `.stat-chip` — بطاقة عمودية بحدود مستديرة وظل، عدد كبير + label صغير.
- `.stat-chip.warn .stat-num { color: #b91c1c; }` (أحمر للمتأخرات).
- `.stat-chip.ok .stat-num { color: #15803d; }` (أخضر للمنجزة).
- `.tasks-toolbar` — flex مع flex-wrap.
- `.kanban-board` — `display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px`.
- `.kanban-column` — بطاقة مع شفافية backdrop-filter وظل، minimum-height 200px.
- `.kanban-header` — حدود سفلية ملوّنة لكل عمود (`#0369a1` / `#a16207` / `#047857`).
- `.kanban-count` — شارة دائرية بلون primary.
- `.status-todo` — لون مميّز للبادج الجديد.
- Media query `@media (max-width: 980px)` يُحوّل Kanban لعمود واحد على الجوال.

---

## 4) الأسبوع الثالث — Technical Integration

### 4.1 endpoints جديدة في `main.py`

#### أ. `POST /tasks/{task_id}/complete`
```python
@app.post("/tasks/{task_id}/complete", response_model=schemas.TaskResponse)
def mark_task_complete(task_id, db, current_user):
    task = db.query(...).filter(id, owner_id).first()
    if not task: raise 404
    task.status = "Completed"
    task.completed_at = datetime.utcnow()
    task.title_updated_at = datetime.utcnow().timestamp()
    db.commit(); db.refresh(task)
    return task
```
- يحدّث 3 أمور بعملية واحدة: الحالة، تاريخ الإكمال، طابع زمني CRDT.
- يُرجع الكائن المحدّث كاملاً.

#### ب. `POST /tasks/{task_id}/reopen`
- يعكس العملية: `status = 'In-Progress'`, `completed_at = None`، تحديث طابع زمني.
- يسمح للمستخدم بإعادة فتح أي مهمة مكتملة.

#### ج. `POST /tasks/import` (Week 3 — JSON I/O)
- يستقبل `TaskImportPayload` (قائمة مهام).
- لكل عنصر:
  - يستدعي `_validate_deadline(item.deadline)`.
  - ينشئ `models.Task` جديداً تحت ملكية المستخدم الحالي.
  - يضع `created_at` و `title_updated_at = desc_updated_at = now`.
- يُرجع `{"created": <count>}`.

#### د. `GET /tasks/export`
- يبني payload JSON يحتوي:
  ```json
  {
    "exported_at": "2026-05-10T...",
    "owner": "username",
    "schema": "task_schema.json",
    "tasks": [ {... 13 حقل لكل مهمة ...} ]
  }
  ```
- يُرجع `StreamingResponse` بـ MIME `application/json` و header `Content-Disposition: attachment; filename="tasks-export.json"` ليبدأ التنزيل تلقائياً في المتصفح.

### 4.2 تحديث `POST /tasks/sync` لمنطق LWW الجديد

**التحسينات الحرجة**:
1. التحقق من القيم المستلمة عبر `_validate_priority/status/deadline` قبل أي تعديل.
2. **ربط `completed_at` بتغيّر الحالة عبر sync**:
   - إذا تحوّلت الحالة إلى `Completed` ولم تكن كذلك → `completed_at = now`.
   - إذا تحوّلت من `Completed` إلى أي شيء آخر → `completed_at = None`.
3. الحفاظ على نفس آلية CRDT (LWW) المنفصلة لـ `title` ولـ `description`.

### 4.3 تحديثات الواجهة الأمامية للأسبوع 3

**أ. `handleMarkCompleted`** أُعيد كتابتها لتستدعي endpoint مخصصة بدل sync كامل:
```jsx
const res = await fetch(`${API_BASE}/tasks/${task.id}/complete`, { method: 'POST', headers: authHeaders() });
```
- أبسط، أسرع، وأكثر دلالة (semantic).
- toast نجاح: `#${task.id} tamamlandı olarak işaretlendi.`.

**ب. `handleReopenTask`** (جديدة):
- تستدعي `/tasks/{id}/reopen`.
- toast: `#${task.id} yeniden açıldı.`.

**ج. `handleExportTasks`** (جديدة):
- تستدعي `/tasks/export`.
- تحوّل الاستجابة إلى `Blob`.
- تنشئ رابط تنزيل ديناميكي بـ `URL.createObjectURL`.
- توهم العنصر `<a>` بضغطة لتنزيل ملف `tasks-export.json`.
- تنظف URL وتعرض toast.

**د. `handleImportTasks`** (جديدة):
- تقرأ ملف JSON المختار من المستخدم بـ `file.text()`.
- تتعامل مع تنسيقين:
  - مصفوفة مباشرة `[{...}, ...]`.
  - أو كائن `{tasks: [...]}` (تنسيق الـ export).
- ترسل `POST /tasks/import` بالحمولة.
- toast نجاح/فشل + تحديث القائمة والإحصائيات + بث WebSocket.

**هـ. تحديث `fetchTasks` و `handleUpdateTask` و `handleDeleteTask`** ليستدعوا `fetchStats()` بعد كل عملية.

### 4.4 اختبارات تناسق البيانات (`backend/tests/`)

#### `tests/__init__.py`
ملف فارغ يجعل `tests` حزمة Python (ضروري للاستيراد النسبي في conftest).

#### `tests/conftest.py`
ثلاث آليات أساسية:

1. **إضافة `backend/` لـ `sys.path`** ديناميكياً ليعمل الاختبار من أي مكان.

2. **Fixture `client`**:
   - يستخدم `tmp_path` من pytest لإنشاء قاعدة بيانات SQLite معزولة لكل اختبار.
   - يضبط `DATABASE_URL` عبر `monkeypatch.setenv` ليلتقطه `database.py`.
   - يُسقط الموديولات `database/models/schemas/main` من cache ليُعاد تحميلها بالاتصال الجديد.
   - يُرجع `TestClient` كـ context manager.

3. **دوال مساعدة**:
   - `register_and_login(client, username, password)` ← يُسجِّل ويدخّل ويُرجع headers مع Bearer token.
   - `create_task(client, headers, **overrides)` ← اختصار لإنشاء مهمة بقيم افتراضية مع إمكانية تجاوزها.

#### `tests/test_tasks.py` — 14 اختبار

| # | اسم الاختبار | ما يتحقّق منه |
|---|----------------|------------------|
| 1 | `test_create_task_with_defaults` | إنشاء مهمة يضبط القيم الافتراضية، `created_at` ليس None، `completed_at = None` |
| 2 | `test_invalid_priority_rejected` | أولوية خاطئة (`Critical`) ← 422 |
| 3 | `test_invalid_status_rejected` | حالة خاطئة (`Cancelled`) ← 422 |
| 4 | `test_invalid_deadline_format_rejected` | تاريخ بصيغة خاطئة (`31-12-2030`) ← 422 |
| 5 | `test_mark_complete_sets_completed_at` | استدعاء `/complete` يضبط الحالة و `completed_at` |
| 6 | `test_reopen_clears_completed_at` | استدعاء `/reopen` يعيد `In-Progress` ويمسح `completed_at` |
| 7 | `test_filter_by_priority_and_status` | فلترة مزدوجة تُرجع المجموعة الصحيحة |
| 8 | `test_search_query_matches_title_and_description` | `?q=rapor` يطابق العنوان والوصف معاً |
| 9 | `test_stats_endpoint` | `total`, `by_status`, `by_priority` صحيحة |
| 10 | `test_overdue_counted_only_if_not_completed` | المهام المنتهية الصلاحية لا تُحسب إن كانت مكتملة |
| 11 | `test_export_then_import_roundtrip` | تصدير من مستخدم → استيراد لمستخدم آخر = نسخ ناجح |
| 12 | `test_lww_sync_only_applies_when_timestamp_newer` | LWW يرفض timestamp قديم ويقبل أحدث |
| 13 | `test_user_cannot_see_other_users_tasks` | عزل البيانات بين المستخدمين |
| 14 | `test_delete_task_removes_it` | الحذف فعّال ويُفرغ القائمة |

**النتيجة**: `14 passed in 15.89s` ✅.

---

## 5) الأسبوع الرابع — Group Stage & Delivery

### 5.1 ملف `backend/WORKFLOW.md`

وثيقة Markdown مهيكلة بـ 5 أقسام:

1. **الأدوار وتدفق البيانات** — رسم ASCII للمعمارية:
   ```
   Frontend ↔ FastAPI ↔ SQLite
        ↑          ↓
        └── WebSocket /ws (broadcast)
   ```

2. **نموذج البيانات (Hafta 1)** — جدول مفصّل بـ 13 حقل وأنواعها وقيودها.

3. **قائمة مهام أسبوعية (Hafta Hafta)** — كل مرحلة مع checkboxes `[x]` لكل ميزة منجزة.

4. **سيناريو End-to-End** — رسم تدفق نصي يربط الخطوات:
   ```
   Login → Görev Oluştur → Düzenle → Filtre → Tamamla
       → Stats → WebSocket → Export → Import → Done
   ```

5. **تعليمات تشغيل واختبار** — 4 أوامر للـ uvicorn، vite، pytest، e2e.

### 5.2 ملف `backend/e2e_test.py`

سكريبت Python يحاكي تدفق المستخدم الحقيقي مقابل سيرفر حي على `127.0.0.1:8000`. يستخدم `requests` بدل httpx لكونه أكثر شعبية في سكريبتات E2E.

**خطوات السكريبت بالتفصيل** (11 مرحلة):

| الخطوة | الوصف |
|---------|--------|
| 1. **Health check** | GET `/docs` للتأكد من أن السيرفر يعمل |
| 2. **Register + Login** | إنشاء مستخدم بـ `uuid` فريد + استخراج JWT |
| 3. **POST /tasks** | إنشاء مهمة كاملة (priority=High, status=To-Do, deadline=2030-12-31) |
| 4. **Filter + Search** | اختبار `?status=To-Do&priority=High&q=akis` ثم `?q=E2E` |
| 5. **Stats** | التأكد أن `total >= 1` و `by_status['To-Do'] >= 1` |
| 6. **Mark Complete** | POST `/complete` ← التأكد من `status=Completed` و `completed_at != None` |
| 7. **Reopen** | POST `/reopen` ← التأكد من `In-Progress` و `completed_at == None` |
| 8. **LWW Stale** | إرسال sync بـ timestamp قديم (1.0) ← يجب ألا يُحدّث العنوان |
| 9. **Export** | GET `/tasks/export` ← يحتوي المهمة |
| 10. **Import** | إنشاء مستخدم ثانٍ، استيراد المهام، التأكد أن `created >= 1` |
| 11. **Cleanup** | DELETE المهمة |

**أدوات مساعدة في السكريبت**:
- `step(label)` ← يطبع " ➜ ..." لتوضيح المرحلة الحالية.
- `assert_ok(condition, message)` ← يطبع ✓/✗ ويخرج بـ `sys.exit(1)` عند الفشل.

**النتيجة الفعلية**: `✓ TÜM E2E ADIMLAR BAŞARIYLA TAMAMLANDI` خلال 2.06 ثانية.

### 5.3 تحديث `backend/requirements.txt`

أُضيف:
```
pytest>=8.0
httpx>=0.27
requests>=2.32
```

- `pytest` ← لتشغيل اختبارات Week 3.
- `httpx` ← يستخدمه `TestClient` داخلياً.
- `requests` ← يستخدمه سكريبت E2E.

---

## 6) ملخص الـ API الجديد بالكامل

| HTTP | المسار | الدور | الإدخالات | الإخراج |
|------|--------|--------|-------------|---------|
| GET | `/tasks` | قائمة مع فلترة | `priority?`, `status?`, `assigned_to?`, `q?`, `sort?` | `List[TaskResponse]` |
| **GET** | **`/tasks/stats`** | إحصائيات | — | `TaskStats` |
| **GET** | **`/tasks/export`** | تنزيل JSON | — | ملف `tasks-export.json` |
| **POST** | **`/tasks/import`** | استيراد JSON | `TaskImportPayload` | `{"created": N}` |
| POST | `/tasks` | إنشاء (محسّن) | Form (مع validators) | `TaskResponse` |
| **POST** | **`/tasks/{id}/complete`** | إكمال | — | `TaskResponse` |
| **POST** | **`/tasks/{id}/reopen`** | إعادة فتح | — | `TaskResponse` |
| POST | `/tasks/sync` | LWW (محسّن) | `TaskSync` | `TaskResponse` |
| DELETE | `/tasks/{id}` | حذف | — | `{"msg": "..."}` |

**الجديد كلياً**: 4 endpoints. **المُحسَّنة**: 4 endpoints.

---

## 7) ملخص الإضافات على الواجهة الأمامية

### State جديدة (7 متغيرات)
`taskStatus`, `editStatus`, `filterPriority`, `filterStatus`, `searchQuery`, `stats`, `importFileRef`.

### دوال جديدة (4)
`fetchStats()`, `handleExportTasks()`, `handleImportTasks(e)`, `handleReopenTask(task)`.

### دوال محدّثة (5)
`fetchAll`, `handleCreateTask`, `handleUpdateTask`, `handleMarkCompleted`, `handleDeleteTask`.

### مكوّنات UI جديدة
1. شريط إحصائيات (6 بطاقات).
2. شريط أدوات (بحث + 2 فلتر + Export + Import).
3. لوحة Kanban (3 أعمدة) بدل الشبكة المسطّحة.
4. زر "Yeniden Aç" بدل زر التمام للمهام المكتملة.
5. عرض `completed_at` في كل بطاقة مكتملة.
6. select إضافي في نموذج الإنشاء + التعديل لاختيار الحالة.

### أنماط CSS جديدة (في `App.css`)
- `.stats-bar`, `.stat-chip`, `.stat-num`, `.stat-lbl`, `.stat-chip.warn`, `.stat-chip.ok`.
- `.tasks-toolbar`.
- `.kanban-board`, `.kanban-column`, `.kanban-header`, `.kanban-count`, `.kanban-body`.
- `.kanban-todo`, `.kanban-prog`, `.kanban-done`.
- `.status-todo` (لون البادج الأزرق).
- Media query للـ responsive.

---

## 8) الميزات التقنية البارزة (Highlights)

| الميزة | الفائدة |
|--------|----------|
| **JSON Schema رسمي** | عقد بيانات قابل للتوليد (codegen) ولأي عميل خارجي |
| **Migration تلقائي SQLite** | لا حاجة لحذف `test.db` أو سكريبت يدوي |
| **Literal enums في Pydantic** | فحص تلقائي 422 بدلاً من شيكات في كل endpoint |
| **isolated test DB** عبر `monkeypatch` + `tmp_path` | كل اختبار في قاعدة بيانات نظيفة 100% |
| **CRDT/LWW محسّن** | `completed_at` يُحدّث تلقائياً مع الحالة |
| **Export/Import JSON** | نقل البيانات بين المستخدمين أو البيئات |
| **Kanban UI** | عرض بصري مشابه لـ Trello / Jira |
| **Search متعدد الحقول** | بحث في title + description + assigned_to في آن واحد |
| **WebSocket تكامل مع كل عملية جديدة** | بث فوري عند Complete / Reopen / Import / Delete |
| **6 إحصائيات لحظية** | لوحة معلومات مدير المشروع |

---

## 9) نتائج الفحوصات النهائية

| الفحص | النتيجة |
|--------|----------|
| **Pytest** (`tests/test_tasks.py`) | ✅ 14 passed in 15.89s |
| **End-to-End Script** (`e2e_test.py`) | ✅ TÜM E2E ADIMLAR BAŞARIYLA TAMAMLANDI |
| **Lint Errors** (Read Lints) | ✅ No linter errors found |
| **Backend** (uvicorn) | ✅ Running on `127.0.0.1:8000` |
| **Frontend** (vite) | ✅ Running on `localhost:5173` |
| **HMR** بعد كل تعديل React | ✅ يعمل بدون refresh |

---

## 10) كيفية تشغيل وتجربة كل ميزة

```bash
# 1) قاعدة البيانات والاختبارات
cd backend
.venv/bin/pytest -q                    # 14 اختبار pytest
.venv/bin/python e2e_test.py           # سكريبت E2E

# 2) السيرفر (إن لم يكن يعمل)
.venv/bin/uvicorn main:app --reload

# 3) الواجهة (إن لم تكن تعمل)
cd ../frontend
npm run dev

# 4) في المتصفح: http://localhost:5173
#    - سجّل دخول
#    - أنشئ مهمة بحالة To-Do
#    - راقب شريط الإحصائيات يتحدّث
#    - استخدم البحث والفلاتر
#    - اضغط "Tamamlandı İşaretle" → ستنتقل لعمود Completed
#    - اضغط "Yeniden Aç" → ستعود لعمود In-Progress
#    - اضغط ⬇ Export → تنزيل JSON
#    - اضغط ⬆ Import → اختر ملف JSON
```

---

## 11) إحصائيات الإضافة

- **عدد الملفات الجديدة**: 6
- **endpoints جديدة كلياً**: 4
- **endpoints مُحسَّنة**: 4
- **اختبارات pytest**: 14 (نسبة نجاح 100%)
- **خطوات اختبار E2E**: 11 (نسبة نجاح 100%)
- **مكوّنات React جديدة**: شريط إحصائيات + شريط أدوات + لوحة Kanban + 2 زر فعل + 2 select + بادج جديد
- **أنماط CSS جديدة**: 13 selector
- **State variables جديدة في الواجهة**: 7
- **Helper functions جديدة في Backend**: 4 (`_validate_priority/status/deadline`, `run_lightweight_migrations`)
- **Pydantic schemas جديدة**: 3 (`TaskStats`, `TaskImportItem`, `TaskImportPayload`)

---

كل ما طلبته مهمة "Person 2 — Task & Data" مغطى بالكامل ومدعوم بالاختبارات.
