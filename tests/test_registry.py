import json
from pathlib import Path

import pytest

from code39.registry import (
    RegistryDataError,
    RegistryLockError,
    RegistryStore,
    RegistryWriteError,
)


def test_registry_store_tracks_generated_references(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.json", tmp_path / "batches.jsonl")

    assert store.get_generated_references() == set()

    store.register_batch(
        ["ATL001", "ATL002"],
        output_file="output/code-39-batch.pdf",
        force=False,
    )

    assert store.get_generated_references() == {"ATL001", "ATL002"}


def test_registry_history_is_append_only(tmp_path: Path) -> None:
    history_path = tmp_path / "batches.jsonl"
    store = RegistryStore(tmp_path / "registry.json", history_path)

    store.register_batch(["ATL001"], output_file="out-1.pdf", force=False)
    store.register_batch(["ATL002"], output_file="out-2.pdf", force=True)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["first_reference"] == "ATL001"
    assert json.loads(lines[1])["force"] is True


def test_load_registry_rejects_corrupted_json(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid", encoding="utf-8")
    store = RegistryStore(registry_path, tmp_path / "batches.jsonl")

    with pytest.raises(RegistryDataError):
        store.load_registry()


def test_read_history_rejects_corrupted_jsonl(tmp_path: Path) -> None:
    history_path = tmp_path / "batches.jsonl"
    history_path.write_text('{"timestamp":"2026-03-18T00:00:00+00:00"}\nnot-json\n', encoding="utf-8")
    store = RegistryStore(tmp_path / "registry.json", history_path)

    with pytest.raises(RegistryDataError):
        store.read_history()


def test_generation_lock_blocks_second_holder(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.json", tmp_path / "batches.jsonl")

    with store.generation_lock():
        with pytest.raises(RegistryLockError):
            with store.generation_lock(timeout_seconds=0.0):
                pass


def test_register_batch_rolls_back_registry_when_history_write_fails(tmp_path: Path) -> None:
    store = RegistryStore(tmp_path / "registry.json", tmp_path / "batches.jsonl")
    store.register_batch(["ATL001"], output_file="out-1.pdf", force=False)

    original_write_history = store._write_history

    def fail_history_write(records: list[dict[str, object]]) -> None:
        raise RegistryWriteError("simulated history failure")

    store._write_history = fail_history_write  # type: ignore[method-assign]
    try:
        with pytest.raises(RegistryWriteError):
            store.register_batch(["ATL002"], output_file="out-2.pdf", force=False)
    finally:
        store._write_history = original_write_history  # type: ignore[method-assign]

    assert store.get_generated_references() == {"ATL001"}
