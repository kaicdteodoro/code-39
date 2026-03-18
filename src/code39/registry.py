"""Local persistence for generated references and batch logs."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class BatchRecord:
    """Information written into the append-only batch history."""

    timestamp: str
    quantity: int
    first_reference: str
    last_reference: str
    output_file: str
    force: bool


class RegistryError(RuntimeError):
    """Base error for registry and history storage failures."""


class RegistryDataError(RegistryError):
    """Raised when a persistence file contains invalid data."""


class RegistryWriteError(RegistryError):
    """Raised when the registry or history cannot be updated safely."""


class RegistryLockError(RegistryError):
    """Raised when another generation process already holds the lock."""


class RegistryStore:
    """Tracks issued references and immutable batch history."""

    def __init__(self, registry_path: Path, history_path: Path) -> None:
        self.registry_path = registry_path
        self.history_path = history_path

    @property
    def lock_path(self) -> Path:
        """Path used to serialize generation runs."""
        return self.registry_path.with_name(f"{self.registry_path.name}.lock")

    def ensure_storage(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.write_text(
                json.dumps({"generated_references": []}, indent=2) + "\n",
                encoding="utf-8",
            )

    @contextmanager
    def generation_lock(
        self, *, timeout_seconds: float = 10.0, poll_interval_seconds: float = 0.1
    ) -> Iterator[None]:
        """Acquire an exclusive lock to prevent overlapping generations."""
        self.ensure_storage()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                descriptor = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(f"pid={os.getpid()}\n")
                    stream.write(f"started_at={datetime.now(UTC).isoformat()}\n")
                break
            except FileExistsError as error:
                if time.monotonic() >= deadline:
                    raise RegistryLockError(
                        f"Generation lock is already held at {self.lock_path}."
                    ) from error
                time.sleep(poll_interval_seconds)

        try:
            yield
        finally:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError as error:
                raise RegistryWriteError(
                    f"Failed to release generation lock at {self.lock_path}."
                ) from error

    def _validate_registry_payload(self, payload: Any) -> dict[str, Any]:
        """Validate the structure expected by the registry file."""
        if not isinstance(payload, dict):
            raise RegistryDataError(
                f"Registry file {self.registry_path} must contain a JSON object."
            )

        references = payload.get("generated_references", [])
        if not isinstance(references, list) or not all(
            isinstance(reference, str) for reference in references
        ):
            raise RegistryDataError(
                f"Registry file {self.registry_path} must contain a string list named "
                "'generated_references'."
            )

        return payload

    def load_registry(self) -> dict[str, Any]:
        self.ensure_storage()
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RegistryDataError(
                f"Registry file {self.registry_path} is corrupted: {error.msg}."
            ) from error
        except OSError as error:
            raise RegistryWriteError(
                f"Could not read registry file {self.registry_path}."
            ) from error
        return self._validate_registry_payload(payload)

    def _write_registry(self, payload: dict[str, Any]) -> None:
        temp_path = self.registry_path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self.registry_path)
        except OSError as error:
            raise RegistryWriteError(
                f"Could not write registry file {self.registry_path}."
            ) from error

    def _write_history(self, records: list[dict[str, Any]]) -> None:
        temp_path = self.history_path.with_suffix(".tmp")
        serialized = "".join(
            json.dumps(record, ensure_ascii=False) + "\n" for record in records
        )
        try:
            temp_path.write_text(serialized, encoding="utf-8")
            temp_path.replace(self.history_path)
        except OSError as error:
            raise RegistryWriteError(
                f"Could not write history file {self.history_path}."
            ) from error

    def get_generated_references(self) -> set[str]:
        data = self.load_registry()
        return set(data.get("generated_references", []))

    def register_batch(self, references: list[str], *, output_file: str, force: bool) -> None:
        if not references:
            raise ValueError("Cannot register an empty batch.")

        self.ensure_storage()
        previous_payload = self.load_registry()
        previous_history = self.read_history()

        current = set(previous_payload.get("generated_references", []))
        current.update(references)
        updated_payload = dict(previous_payload)
        updated_payload["generated_references"] = sorted(current)

        record = BatchRecord(
            timestamp=datetime.now(UTC).isoformat(),
            quantity=len(references),
            first_reference=references[0],
            last_reference=references[-1],
            output_file=output_file,
            force=force,
        )
        updated_history = [*previous_history, asdict(record)]

        self._write_registry(updated_payload)
        try:
            self._write_history(updated_history)
        except RegistryWriteError as error:
            try:
                self._write_registry(previous_payload)
            except RegistryWriteError as rollback_error:
                raise RegistryWriteError(
                    "History update failed and registry rollback could not be completed."
                ) from rollback_error
            raise RegistryWriteError(
                "History update failed after registry write. Registry rollback completed."
            ) from error

    def read_history(self) -> list[dict[str, Any]]:
        self.ensure_storage()
        if not self.history_path.exists():
            return []
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise RegistryWriteError(
                f"Could not read history file {self.history_path}."
            ) from error

        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise RegistryDataError(
                    f"History file {self.history_path} is corrupted at line "
                    f"{line_number}: {error.msg}."
                ) from error

            if not isinstance(payload, dict):
                raise RegistryDataError(
                    f"History file {self.history_path} contains a non-object record at "
                    f"line {line_number}."
                )
            records.append(payload)
        return records
