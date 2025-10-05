"""Хранилище состояния обработки сообщений."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .logger import get_logger

try:
    import orjson as json_lib
except ImportError:  # pragma: no cover
    import json as json_lib


DEFAULT_STATE = {"last_seen_id": 0}


@dataclass(slots=True)
class ProcessingState:
    """Состояние обработки сообщений."""

    last_seen_id: int = 0


class StateStore:
    """Файловое хранилище состояния."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.logger = get_logger(__name__)

    def read(self) -> ProcessingState:
        """Читает состояние из файла."""

        if not self.path.exists():
            self.logger.info(
                "Создание нового файла состояния",
                context={"path": str(self.path)},
            )
            self._write(DEFAULT_STATE)
            return ProcessingState()

        raw = self.path.read_bytes()
        data = json_lib.loads(raw)
        return ProcessingState(last_seen_id=int(data.get("last_seen_id", 0)))

    def update_last_seen(self, *, message_id: int, dry_run: bool) -> ProcessingState:
        """Обновляет идентификатор последнего обработанного сообщения."""

        state = self.read()
        if message_id <= state.last_seen_id:
            return state

        if dry_run:
            self.logger.info(
                "DRY_RUN: состояние не сохранено",
                context={"candidate_id": message_id},
            )
            return ProcessingState(last_seen_id=message_id)

        self._write({"last_seen_id": message_id})
        self.logger.info(
            "Состояние обновлено",
            context={"last_seen_id": message_id},
        )
        return ProcessingState(last_seen_id=message_id)

    def _write(self, data: dict) -> None:
        serialized = json_lib.dumps(data)
        if isinstance(serialized, bytes):
            self.path.write_bytes(serialized)
        else:  # pragma: no cover
            self.path.write_text(serialized, encoding="utf-8")
