"""Person 2 — Hafta 3: Veri Tutarlılık (Data Consistency) Testleri."""
from __future__ import annotations

from .conftest import create_task, register_and_login


def test_create_task_with_defaults(client):
    headers = register_and_login(client)
    task = create_task(client, headers, title="İlk görev")
    assert task["id"] > 0
    assert task["status"] == "To-Do"
    assert task["priority"] == "Normal"
    assert task["completed_at"] is None
    assert task["created_at"] is not None


def test_invalid_priority_rejected(client):
    headers = register_and_login(client)
    res = client.post(
        "/tasks",
        data={
            "title": "X", "description": "Y", "priority": "Critical",
            "status": "To-Do", "title_at": 1.0, "desc_at": 1.0,
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_invalid_status_rejected(client):
    headers = register_and_login(client)
    res = client.post(
        "/tasks",
        data={
            "title": "X", "description": "Y", "priority": "Normal",
            "status": "Cancelled", "title_at": 1.0, "desc_at": 1.0,
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_invalid_deadline_format_rejected(client):
    headers = register_and_login(client)
    res = client.post(
        "/tasks",
        data={
            "title": "X", "description": "Y", "priority": "Normal",
            "status": "To-Do", "deadline": "31-12-2030",
            "title_at": 1.0, "desc_at": 1.0,
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_mark_complete_sets_completed_at(client):
    headers = register_and_login(client)
    task = create_task(client, headers, title="Tamamlanacak")
    res = client.post(f"/tasks/{task['id']}/complete", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "Completed"
    assert body["completed_at"] is not None


def test_reopen_clears_completed_at(client):
    headers = register_and_login(client)
    task = create_task(client, headers, status="Completed")
    client.post(f"/tasks/{task['id']}/complete", headers=headers)
    res = client.post(f"/tasks/{task['id']}/reopen", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "In-Progress"
    assert body["completed_at"] is None


def test_filter_by_priority_and_status(client):
    headers = register_and_login(client)
    create_task(client, headers, title="A", priority="High", status="To-Do")
    create_task(client, headers, title="B", priority="Low", status="In-Progress")
    create_task(client, headers, title="C", priority="High", status="In-Progress")

    res = client.get("/tasks?priority=High", headers=headers)
    assert res.status_code == 200
    assert {t["title"] for t in res.json()} == {"A", "C"}

    res = client.get("/tasks?status=In-Progress&priority=High", headers=headers)
    assert {t["title"] for t in res.json()} == {"C"}


def test_search_query_matches_title_and_description(client):
    headers = register_and_login(client)
    create_task(client, headers, title="Rapor hazırla", description="Hafta sonu için")
    create_task(client, headers, title="Toplantı", description="Rapor sunumu")
    create_task(client, headers, title="Mola", description="Kahve")

    res = client.get("/tasks?q=rapor", headers=headers)
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Rapor hazırla", "Toplantı"}


def test_stats_endpoint(client):
    headers = register_and_login(client)
    create_task(client, headers, status="To-Do", priority="High")
    create_task(client, headers, status="In-Progress", priority="Normal")
    t = create_task(client, headers, status="To-Do", priority="Low")
    client.post(f"/tasks/{t['id']}/complete", headers=headers)

    res = client.get("/tasks/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["total"] == 3
    assert stats["by_status"]["Completed"] == 1
    assert stats["by_status"]["To-Do"] == 1
    assert stats["by_status"]["In-Progress"] == 1
    assert stats["by_priority"]["High"] == 1


def test_overdue_counted_only_if_not_completed(client):
    headers = register_and_login(client)
    create_task(client, headers, title="Eski", deadline="2000-01-01", status="To-Do")
    done = create_task(client, headers, title="Eski tamam", deadline="2000-01-01", status="To-Do")
    client.post(f"/tasks/{done['id']}/complete", headers=headers)

    stats = client.get("/tasks/stats", headers=headers).json()
    assert stats["overdue"] == 1


def test_export_then_import_roundtrip(client):
    headers = register_and_login(client)
    create_task(client, headers, title="Export-1", priority="High", status="To-Do")
    create_task(client, headers, title="Export-2", priority="Low", status="In-Progress")

    export_res = client.get("/tasks/export", headers=headers)
    assert export_res.status_code == 200
    payload = export_res.json()
    assert len(payload["tasks"]) == 2

    headers2 = register_and_login(client, username="bob", password="Strong#Pass1")
    items = [
        {
            "title": t["title"],
            "description": t["description"],
            "priority": t["priority"],
            "status": t["status"],
            "deadline": t["deadline"],
            "assigned_to": t["assigned_to"],
        }
        for t in payload["tasks"]
    ]
    import_res = client.post("/tasks/import", json={"tasks": items}, headers=headers2)
    assert import_res.status_code == 200
    assert import_res.json()["created"] == 2

    bob_tasks = client.get("/tasks", headers=headers2).json()
    assert {t["title"] for t in bob_tasks} == {"Export-1", "Export-2"}


def test_lww_sync_only_applies_when_timestamp_newer(client):
    headers = register_and_login(client)
    task = create_task(client, headers, title="Orijinal", title_at=100.0, desc_at=100.0)

    stale = {
        "id": task["id"],
        "title": "Eski güncelleme",
        "description": "Eski açıklama",
        "priority": "High",
        "status": "In-Progress",
        "deadline": None,
        "assigned_to": None,
        "title_updated_at": 50.0,
        "desc_updated_at": 50.0,
    }
    res = client.post("/tasks/sync", json=stale, headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Orijinal"

    fresh = {**stale, "title": "Yeni başlık", "title_updated_at": 200.0, "desc_updated_at": 200.0,
             "description": "Yeni açıklama"}
    res = client.post("/tasks/sync", json=fresh, headers=headers)
    assert res.json()["title"] == "Yeni başlık"
    assert res.json()["description"] == "Yeni açıklama"


def test_user_cannot_see_other_users_tasks(client):
    h_alice = register_and_login(client, "alice2")
    create_task(client, h_alice, title="Gizli")

    h_bob = register_and_login(client, "bob2")
    res = client.get("/tasks", headers=h_bob)
    assert res.status_code == 200
    assert res.json() == []


def test_delete_task_removes_it(client):
    headers = register_and_login(client)
    task = create_task(client, headers, title="Silinecek")
    res = client.delete(f"/tasks/{task['id']}", headers=headers)
    assert res.status_code == 200
    listing = client.get("/tasks", headers=headers).json()
    assert listing == []
