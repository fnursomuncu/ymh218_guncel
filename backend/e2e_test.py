"""Person 2 — Hafta 4: End-to-End Workflow doğrulama scripti.

Çalıştırmadan önce sunucunun ayakta olduğundan emin olun:
    .venv/bin/uvicorn main:app --reload

Sonra:
    .venv/bin/python e2e_test.py
"""
from __future__ import annotations

import sys
import time
import uuid

import requests

BASE = "http://127.0.0.1:8000"


def step(label: str) -> None:
    print(f"\n  ➜ {label}")


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        print(f"  ✗ FAIL: {message}")
        sys.exit(1)
    print(f"  ✓ {message}")


def main() -> None:
    suffix = uuid.uuid4().hex[:6]
    user = f"e2e_{suffix}"
    pw = "Strong#Pass1"

    step("Sunucu sağlık kontrolü")
    try:
        r = requests.get(f"{BASE}/docs", timeout=5)
        assert_ok(r.status_code == 200, "Sunucu /docs cevap veriyor")
    except requests.RequestException as exc:
        print(f"  ✗ Sunucuya ulaşılamadı: {exc}")
        sys.exit(1)

    step("Kayıt + giriş")
    r = requests.post(f"{BASE}/register", json={"username": user, "email": f"{user}@e2e.local", "password": pw})
    assert_ok(r.status_code == 200, "Kullanıcı kaydı tamamlandı")
    r = requests.post(f"{BASE}/login", json={"identifier": user, "password": pw})
    assert_ok(r.status_code == 200, "Giriş başarılı")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    step("Yeni görev oluştur")
    now = time.time()
    r = requests.post(
        f"{BASE}/tasks",
        data={
            "title": "E2E akış görevi",
            "description": "Tam workflow testi",
            "priority": "High",
            "status": "To-Do",
            "deadline": "2030-12-31",
            "assigned_to": "QA",
            "title_at": now,
            "desc_at": now,
        },
        headers=headers,
    )
    assert_ok(r.status_code == 200, "POST /tasks 200")
    task = r.json()
    assert_ok(task["status"] == "To-Do" and task["priority"] == "High", "İlk durum/öncelik doğru")

    step("Filtre & arama")
    r = requests.get(f"{BASE}/tasks?status=To-Do&priority=High&q=akis", headers=headers)
    assert_ok(r.status_code == 200, "Filtreli liste 200")
    r = requests.get(f"{BASE}/tasks?q=E2E", headers=headers)
    assert_ok(any(t["id"] == task["id"] for t in r.json()), "Arama görevi buldu")

    step("İstatistikler")
    stats = requests.get(f"{BASE}/tasks/stats", headers=headers).json()
    assert_ok(stats["total"] >= 1, "Stats: total >= 1")
    assert_ok(stats["by_status"]["To-Do"] >= 1, "Stats: To-Do >= 1")

    step("Tamamlandı işaretle")
    r = requests.post(f"{BASE}/tasks/{task['id']}/complete", headers=headers)
    assert_ok(r.status_code == 200, "Complete endpoint 200")
    completed = r.json()
    assert_ok(completed["status"] == "Completed", "Durum Completed oldu")
    assert_ok(completed["completed_at"] is not None, "completed_at zaman damgası set edildi")

    step("Yeniden aç")
    r = requests.post(f"{BASE}/tasks/{task['id']}/reopen", headers=headers)
    assert_ok(r.json()["status"] == "In-Progress", "Reopen → In-Progress")
    assert_ok(r.json()["completed_at"] is None, "Reopen → completed_at temizlendi")

    step("LWW sync (eski timestamp ignored)")
    stale = {
        "id": task["id"],
        "title": "ESKI", "description": "ESKI",
        "priority": "Low", "status": "To-Do",
        "deadline": None, "assigned_to": None,
        "title_updated_at": 1.0, "desc_updated_at": 1.0,
    }
    r = requests.post(f"{BASE}/tasks/sync", json=stale, headers=headers)
    assert_ok(r.json()["title"] == "E2E akış görevi", "Eski timestamp uygulanmadı")

    step("JSON Export")
    r = requests.get(f"{BASE}/tasks/export", headers=headers)
    assert_ok(r.status_code == 200, "Export 200")
    payload = r.json()
    assert_ok(any(t["id"] == task["id"] for t in payload["tasks"]), "Export içeriği doğru")

    step("İkinci kullanıcıya Import")
    user2 = f"e2eb_{suffix}"
    requests.post(f"{BASE}/register", json={"username": user2, "email": f"{user2}@e2e.local", "password": pw})
    tok2 = requests.post(f"{BASE}/login", json={"identifier": user2, "password": pw}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {tok2}"}
    items = [{
        "title": t["title"], "description": t["description"], "priority": t["priority"],
        "status": t["status"], "deadline": t["deadline"], "assigned_to": t["assigned_to"],
    } for t in payload["tasks"]]
    r = requests.post(f"{BASE}/tasks/import", json={"tasks": items}, headers=h2)
    assert_ok(r.status_code == 200 and r.json()["created"] >= 1, "Import 200, en az 1 görev kopyalandı")

    step("Temizlik")
    r = requests.delete(f"{BASE}/tasks/{task['id']}", headers=headers)
    assert_ok(r.status_code == 200, "Görev silindi")

    print("\n✓ TÜM E2E ADIMLAR BAŞARIYLA TAMAMLANDI")


if __name__ == "__main__":
    main()
