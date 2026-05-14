# Görev Yöneticisi — Person 2 Workflow (Task & Data)

Bu doküman, **2nd Person — Task & Data** rolünün dört haftalık iş akışını ve sistemin uçtan uca (end-to-end) çalışma mantığını açıklar.

## 1. Roller ve Veri Akışı

```
 ┌────────────┐   POST /tasks            ┌─────────────────┐
 │   Frontend │ ───────────────────────▶ │   FastAPI API   │
 │   (React)  │ ◀────────────────────── │ (validation +   │
 └────────────┘   GET /tasks?filters     │  consistency)   │
        ▲                                 └─────────────────┘
        │   WebSocket /ws (broadcast)             │
        │                                         ▼
        │                                 ┌─────────────────┐
        └─────────  realtime  ──────────  │  SQLite (tasks) │
                                          └─────────────────┘
```

## 2. Veri Modeli (Hafta 1)

JSON şeması: [`task_schema.json`](./task_schema.json)

| Alan | Tip | Notlar |
|------|-----|--------|
| `id` | int | Sunucu üretir |
| `title` | string (1..120) | Zorunlu |
| `description` | string (1..2000) | Zorunlu |
| `priority` | enum | `High` \| `Normal` \| `Low` |
| `status` | enum | `To-Do` \| `In-Progress` \| `Completed` |
| `deadline` | string (date) \| null | `YYYY-MM-DD` |
| `assigned_to` | string \| null | |
| `created_at` | datetime | UTC, otomatik |
| `completed_at` | datetime \| null | "Tamamlandı" anında set edilir |
| `title_updated_at` | float | LWW (CRDT) için |
| `desc_updated_at` | float | LWW (CRDT) için |

## 3. Hafta Hafta Görev Listesi

### Hafta 1 — Initialization & Basic Structure
- [x] JSON şeması oluşturuldu (`task_schema.json`)
- [x] Modeller `created_at`, `completed_at`, enum alanlarıyla güncellendi
- [x] SQLite üzerinde otomatik kolon migration (`run_lightweight_migrations`)

### Hafta 2 — Development & Interface
- [x] `POST /tasks` — öncelik + durum + deadline destekli
- [x] `GET /tasks` — `priority`, `status`, `assigned_to`, `q`, `sort` parametreleri
- [x] `GET /tasks/stats` — toplam, durum, öncelik, gecikmiş, bu hafta tamamlanan
- [x] React arayüzü: arama, filtre, istatistik şeridi, 3 kolonlu Kanban, JSON Export/Import

### Hafta 3 — Technical Integration
- [x] `POST /tasks/{id}/complete` — durumu `Completed` yapar, `completed_at` ayarlar
- [x] `POST /tasks/{id}/reopen` — durumu `In-Progress` yapar, `completed_at` temizler
- [x] CRDT/LWW `/tasks/sync` — sadece daha yeni timestamp'lerde uygular
- [x] Pytest suite (`tests/test_tasks.py`) — 14+ veri tutarlılık testi

### Hafta 4 — Group Stage & Delivery
- [x] WORKFLOW.md (bu dosya)
- [x] End-to-end senaryo: `e2e_test.py`

## 4. End-to-End Senaryo (Workflow Diagram)

```
[Login] → [Görev Oluştur (To-Do)] → [Düzenle / Önceliği Yükselt]
   ↓
[Filtre: status=To-Do] → [Tamamlandı İşaretle] → [Kanban: Completed sütunu]
   ↓
[İstatistikler güncellenir]   [WebSocket → diğer istemciler bilgilendirilir]
   ↓
[JSON Export] → [Yeni kullanıcıya Import] → [Veri tutarlılığı doğrulandı]
```

## 5. Çalıştırma & Test

```bash
# API
cd backend
.venv/bin/uvicorn main:app --reload

# Frontend
cd frontend
npm run dev

# Birim/entegrasyon testleri
cd backend
.venv/bin/pytest -q

# E2E (sunucu çalışırken)
.venv/bin/python e2e_test.py
```
