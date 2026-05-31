from __future__ import annotations

from abc import ABC
from typing import Any

from .errors import TableAlreadyExistsError, TableNotFoundError
from .table import Table, TableRecord


class DatabaseManager(ABC):
    def __init__(self) -> None:
        self._tables: list[Table] = []

    def reset(self) -> None:
        self._tables.clear()

    def create_base(
        self,
        name: str,
        columns: list[str],
        indexed_fields: list[str] | None = None,
    ) -> Table:
        if self._find_table_index_by_name(name) is not None:
            raise TableAlreadyExistsError(f"Таблица '{name}' уже существует.")

        table = Table(name, columns, indexed_fields=indexed_fields)
        self._tables.append(table)
        self._save_table(table)
        return table

    def delete_base(self, index: int) -> None:
        table = self.get_table(index)
        del self._tables[index]
        self._delete_table_storage(table.name)

    def return_bases(self) -> list[list[Any]]:
        return [[table.name, table.columns, table.get_records()] for table in self._tables]

    def get_tmp(self, number_of_base: int) -> list[str]:
        return self.get_table(number_of_base).columns

    def get_table(self, number_of_base: int) -> Table:
        try:
            return self._tables[number_of_base]
        except IndexError as exc:
            raise TableNotFoundError(f"Таблица с индексом {number_of_base} не существует.") from exc

    def create_record(self, number_of_base: int, values: list[Any]) -> TableRecord:
        table = self.get_table(number_of_base)
        record = table.create_record(values)
        self._save_table(table)
        return record

    def select_records(self, number_of_base: int, filters: list[Any] | None = None) -> list[TableRecord]:
        return self.get_table(number_of_base).select_records(filters)

    def update_record(self, number_of_base: int, record_index: int, new_values: list[Any]) -> TableRecord:
        table = self.get_table(number_of_base)
        updated = table.update_record(record_index, new_values)
        self._save_table(table)
        return updated

    def delete_record(self, number_of_base: int, result: list[TableRecord], n: int = 0) -> bool:
        table = self.get_table(number_of_base)
        deleted = table.delete_record(result, n)
        if deleted:
            self._save_table(table)
        return deleted

    def sort_records(
        self,
        number_of_base: int,
        field: int | str,
        reverse: bool = False,
    ) -> list[TableRecord]:
        table = self.get_table(number_of_base)
        sorted_records = table.sort_records(field, reverse)
        self._save_table(table)
        return sorted_records

    def create_index(self, number_of_base: int, fields: list[str]) -> list[str]:
        table = self.get_table(number_of_base)
        table.create_index(*fields)
        self._save_table(table)
        return table.indexed_fields

    def _find_table_index_by_name(self, name: str) -> int | None:
        cleaned_name = name.strip()
        for index, table in enumerate(self._tables):
            if table.name == cleaned_name:
                return index
        return None

    def _save_table(self, table: Table) -> None:
        return None

    def _delete_table_storage(self, table_name: str) -> None:
        return None
