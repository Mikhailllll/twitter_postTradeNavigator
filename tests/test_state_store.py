"""Тесты для хранилища состояния."""

from __future__ import annotations

from src.state_store import StateStore


def test_state_store_creates_file(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    state = store.read()
    assert state.last_seen_id == 0
    assert path.exists()


def test_state_store_updates_and_respects_dry_run(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.read()

    updated = store.update_last_seen(message_id=5, dry_run=True)
    assert updated.last_seen_id == 5
    persisted = store.read()
    assert persisted.last_seen_id == 0

    store.update_last_seen(message_id=7, dry_run=False)
    saved = store.read()
    assert saved.last_seen_id == 7


def test_state_store_recovers_from_corrupted_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not-a-json", encoding="utf-8")
    store = StateStore(path)

    state = store.read()

    assert state.last_seen_id == 0
    assert path.read_text(encoding="utf-8") == "{\"last_seen_id\":0}"
