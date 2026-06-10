from __future__ import annotations

import json
from pathlib import Path

from .errors import InvalidStorageDataError
from .storage import FileDatabaseManager


class JsonDatabaseManager(FileDatabaseManager):
    file_extension = ".json"

    def _read_storage(self, path: Path) -> object:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise InvalidStorageDataError(f"Файл '{path.name}' содержит некорректный JSON.") from exc

    def _write_storage(self, path: Path, data: object) -> None:
        try:
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except (OSError, TypeError, PermissionError, json.JSONDecodeError) as exc:
            raise InvalidStorageDataError(
                f"Не удалось записать JSON в файл '{path.name}'."
            ) from exc