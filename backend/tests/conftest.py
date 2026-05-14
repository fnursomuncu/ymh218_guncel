"""Test fixtures: izole bir SQLite veritabanı kullanarak FastAPI uygulamasını test eder."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Her test için temiz, geçici bir SQLite veritabanı oluşturur."""
    db_file = tmp_path / "test_tasks.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    for mod in ("database", "models", "schemas", "main"):
        sys.modules.pop(mod, None)

    from fastapi.testclient import TestClient
    import main

    with TestClient(main.app) as test_client:
        yield test_client


def register_and_login(client, username="alice", password="Strong#Pass1"):
    client.post(
        "/register",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    res = client.post("/login", json={"identifier": username, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_task(client, headers, **overrides):
    payload = {
        "title": overrides.get("title", "Test görev"),
        "description": overrides.get("description", "Açıklama"),
        "priority": overrides.get("priority", "Normal"),
        "status": overrides.get("status", "To-Do"),
        "deadline": overrides.get("deadline", ""),
        "assigned_to": overrides.get("assigned_to", ""),
        "title_at": overrides.get("title_at", 1.0),
        "desc_at": overrides.get("desc_at", 1.0),
    }
    res = client.post("/tasks", data=payload, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()
