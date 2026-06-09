from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .database import DatabaseManager
from .errors import InvalidStorageDataError
from .table import Table


class FileDatabaseManager(DatabaseManager, ABC):
    file_extension = ""

    def __init__(self, directory: str) -> None:
        super().__init__()
        self.directory = Path(directory)
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise InvalidStorageDataError(
                f"Не удалось создать или открыть директорию хранения '{directory}'."
            ) from exc
        self._tables = self._load_tables()

    def reset(self) -> None:
        self._tables = self._load_tables()

    def _load_tables(self) -> list[Table]:
        tables: list[Table] = []
        for path in sorted(self.directory.glob(f"*{self.file_extension}")):
            table_name = path.stem
            data = self._read_storage(path)
            try:
                table = self._deserialize_table(table_name, data)
            except (KeyError, TypeError, ValueError) as exc:
                raise InvalidStorageDataError(f"Некорректные данные в файле '{path.name}'.") from exc
            tables.append(table)
        return tables

    def _save_table(self, table: Table) -> None:
        path = self.directory / f"{table.name}{self.file_extension}"
        self._write_storage(path, self._serialize_table(table))

    def _delete_table_storage(self, table_name: str) -> None:
        path = self.directory / f"{table_name}{self.file_extension}"
        if path.exists():
            path.unlink()

    def _serialize_table(self, table: Table) -> object:
        return {
            "columns": table.columns,
            "indexed_fields": table.indexed_fields,
            "records": [list(record) for record in table.get_records()],
        }

    def _deserialize_table(self, table_name: str, data: object) -> Table:
        if not isinstance(data, dict):
            raise InvalidStorageDataError("Сохранённая таблица должна быть словарём.")

        columns = data["columns"]
        indexed_fields = data.get("indexed_fields")
        records = data.get("records", [])
        return Table(table_name, columns, records=records, indexed_fields=indexed_fields)

    @abstractmethod
    def _read_storage(self, path: Path) -> object:
        """Read raw table data from a storage file."""

    @abstractmethod
    def _write_storage(self, path: Path, data: object) -> None:
        """Write raw table data to a storage file."""
