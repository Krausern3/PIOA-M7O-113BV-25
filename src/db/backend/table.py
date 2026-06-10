from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


type TableRecord = tuple[Any, ...]


class Table:
    def __init__(
        self,
        name: str,
        columns: Iterable[str],
        records: Iterable[Sequence[Any]] | None = None,
        indexed_fields: Iterable[str] | None = None,
    ) -> None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Имя таблицы не может быть пустым.")

        cleaned_columns = [column.strip() for column in columns if column.strip()]
        if not cleaned_columns:
            raise ValueError("Нужно указать хотя бы один столбец.")
        if len(cleaned_columns) != len(set(cleaned_columns)):
            raise ValueError("Имена столбцов должны быть уникальными.")

        self.name = cleaned_name
        self._columns = cleaned_columns
        self._records: list[TableRecord] = []
        self._indexed_fields: list[str] = []
        self._indexes: dict[str, dict[Any, set[int]]] = {}
        self.create_index(*(indexed_fields or cleaned_columns))

        for record in records or []:
            self._append_existing_record(record)

    @property
    def columns(self) -> list[str]:
        return self._columns.copy()

    @property
    def indexed_fields(self) -> list[str]:
        return self._indexed_fields.copy()

    def get_records(self) -> list[TableRecord]:
        return self._records.copy()

    def create_index(self, *fields: str) -> None:
        normalized_fields = [field.strip() for field in fields if field and field.strip()]
        if not normalized_fields:
            normalized_fields = self._columns.copy()

        unknown_fields = [field for field in normalized_fields if field not in self._columns]
        if unknown_fields:
            raise ValueError(f"Неизвестные поля для индексации: {', '.join(unknown_fields)}.")

        self._indexed_fields = list(dict.fromkeys(normalized_fields))
        self._rebuild_indexes()

    def create_record(self, values: list[Any]) -> TableRecord:
        if len(values) != len(self._columns):
            raise ValueError(f"Ожидалось {len(self._columns)} значений, получено {len(values)}.")

        record = tuple(value.strip() if isinstance(value, str) else value for value in values)
        self._ensure_unique_primary_key(record[0])
        self._records.append(record)
        self._index_record(len(self._records) - 1, record)
        return record

    def select_records(self, filters: list[Any] | None = None) -> list[TableRecord]:
        if not filters:
            return self._records.copy()

        candidate_positions = self._get_candidate_positions(filters)
        positions = candidate_positions if candidate_positions is not None else range(len(self._records))

        result: list[TableRecord] = []
        for position in positions:
            record = self._records[position]
            if self._matches_filters(record, filters):
                result.append(record)
        return result

    def update_record(self, record_index: int, new_values: list[Any]) -> TableRecord:
        if not 0 <= record_index < len(self._records):
            raise ValueError(f"Запись с индексом {record_index} не существует.")

        current_record = list(self._records[record_index])
        for index, value in enumerate(new_values[: len(current_record)]):
            if value is None:
                continue
            current_record[index] = value.strip() if isinstance(value, str) else value

        updated_record = tuple(current_record)
        self._ensure_unique_primary_key(updated_record[0], ignore_index=record_index)
        self._records[record_index] = updated_record
        self._rebuild_indexes()
        return updated_record

    def delete_record(self, result: list[TableRecord], n: int = 0) -> bool:
        if not 0 <= n < len(result):
            return False

        try:
            self._records.remove(result[n])
        except ValueError:
            return False

        self._rebuild_indexes()
        return True

    def sort_records(self, field: int | str, reverse: bool = False) -> list[TableRecord]:
        field_index = self._resolve_field_index(field)
        self._records = sorted(self._records, key=lambda record: record[field_index], reverse=reverse)
        self._rebuild_indexes()
        return self._records.copy()

    def _append_existing_record(self, values: Sequence[Any]) -> None:
        if len(values) != len(self._columns):
            raise ValueError(f"Сохранённая запись таблицы '{self.name}' имеет неверное число столбцов.")

        record = tuple(values)
        self._ensure_unique_primary_key(record[0])
        self._records.append(record)
        self._index_record(len(self._records) - 1, record)

    def _ensure_unique_primary_key(self, primary_key: Any, ignore_index: int | None = None) -> None:
        for idx, record in enumerate(self._records):
            if idx == ignore_index:
                continue
            if record[0] == primary_key:
                raise ValueError(f"Запись с id={primary_key} уже существует.")

    def _get_candidate_positions(self, filters: list[Any]) -> list[int] | None:
        candidate_positions: set[int] | None = None
        for index, filter_value in enumerate(filters[: len(self._columns)]):
            if filter_value in (None, ""):
                continue

            column = self._columns[index]
            if column not in self._indexes:
                continue

            matching_positions = self._indexes[column].get(filter_value, set())
            if not matching_positions and isinstance(filter_value, (int, float)):
                str_key = str(filter_value)
                matching_positions = self._indexes[column].get(str_key, set())
            candidate_positions = (
                set(matching_positions)
                if candidate_positions is None
                else candidate_positions & matching_positions
            )

            if not candidate_positions:
                return []

        return sorted(candidate_positions) if candidate_positions is not None else None

    def _matches_filters(self, record: TableRecord, filters: list[Any]) -> bool:
        for index, filter_value in enumerate(filters[: len(self._columns)]):
            if filter_value in (None, ""):
                continue

            record_value = record[index]

            if record_value != filter_value:
                try:
                    if isinstance(record_value, str) and isinstance(filter_value, (int, float)):
                        if float(record_value) == float(filter_value):
                            continue
                    elif isinstance(filter_value, str) and isinstance(record_value, (int, float)):
                        if float(filter_value) == float(record_value):
                            continue
                except (ValueError, TypeError):
                    pass
                return False
        return True

    def _resolve_field_index(self, field: int | str) -> int:
        if isinstance(field, int):
            if 0 <= field < len(self._columns):
                return field
            raise ValueError("Индекс поля сортировки вне диапазона.")

        try:
            return self._columns.index(field)
        except ValueError as exc:
            raise ValueError(f"Неизвестное поле сортировки: {field}.") from exc

    def _rebuild_indexes(self) -> None:
        self._indexes = {field: {} for field in self._indexed_fields}
        for position, record in enumerate(self._records):
            self._index_record(position, record)

    def _index_record(self, position: int, record: TableRecord) -> None:
        for field in self._indexed_fields:
            field_index = self._columns.index(field)
            value = record[field_index]
            bucket = self._indexes[field].setdefault(value, set())
            bucket.add(position)
