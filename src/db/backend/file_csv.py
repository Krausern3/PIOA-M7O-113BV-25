from __future__ import annotations

import csv
from pathlib import Path

from .errors import InvalidStorageDataError
from .storage import FileDatabaseManager
from .table import Table


class CsvDatabaseManager(FileDatabaseManager):
    file_extension = ".csv"
    _metadata_marker = "__indexed_fields__"

    def _read_storage(self, path: Path) -> object:
        with path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file))

        if not rows:
            raise InvalidStorageDataError(f"Файл '{path.name}' пуст.")
        return rows

    def _write_storage(self, path: Path, data: object) -> None:
        if not isinstance(data, list):
            raise InvalidStorageDataError("CSV-хранилище ожидает список строк.")

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data)

    def _serialize_table(self, table: Table) -> object:
        rows: list[list[str]] = [
            table.columns,
            [self._metadata_marker, *table.indexed_fields],
        ]
        rows.extend([[str(value) for value in record] for record in table.get_records()])
        return rows

    def _deserialize_table(self, table_name: str, data: object) -> Table:
        if not isinstance(data, list) or not data or not all(isinstance(row, list) for row in data):
            raise InvalidStorageDataError("CSV-хранилище должно содержать строки.")

        columns = data[0]
        rows = data[1:]
        indexed_fields = columns
        if rows and rows[0] and rows[0][0] == self._metadata_marker:
            indexed_fields = [field for field in rows[0][1:] if field]
            rows = rows[1:]

        for row in rows:
            if len(row) != len(columns):
                raise InvalidStorageDataError(
                    f"Длина строки CSV в таблице '{table_name}' не совпадает с числом столбцов."
                )

        return Table(table_name, columns, records=rows, indexed_fields=indexed_fields)
