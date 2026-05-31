from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .errors import DuplicateIDError, InvalidAgeError

type StudentRecord = tuple[int, str, str, int, str]
type TableRecord = tuple[Any, ...]


class StudentTable:
    def __init__(self) -> None:
        self._students: list[StudentRecord] = []

    def create_record(
        self,
        student_id: int,
        first_name: str,
        second_name: str,
        age: int,
        sex: str,
    ) -> StudentRecord:
        if age < 0:
            raise InvalidAgeError("Поле age не может быть отрицательным.")
        if any(record[0] == student_id for record in self._students):
            raise DuplicateIDError(f"Запись с id={student_id} уже существует.")

        record: StudentRecord = (
            student_id,
            first_name.strip(),
            second_name.strip(),
            age,
            sex.strip(),
        )
        self._students.append(record)
        return record

    def select_record(
        self,
        student_id: int | None = None,
        first_name: str | None = None,
        second_name: str | None = None,
        age: int | None = None,
        sex: str | None = None,
    ) -> list[StudentRecord]:
        filters = (student_id, first_name, second_name, age, sex)
        if all(value is None for value in filters):
            return self._students.copy()

        result: list[StudentRecord] = []
        for record in self._students:
            if student_id is not None and record[0] != student_id:
                continue
            if first_name is not None and record[1] != first_name:
                continue
            if second_name is not None and record[2] != second_name:
                continue
            if age is not None and record[3] != age:
                continue
            if sex is not None and record[4] != sex:
                continue
            result.append(record)
        return result

    def sort_records(self, field: int | str, reverse: bool = False) -> list[StudentRecord]:
        field_index = self._resolve_student_field(field)
        self._students = sorted(self._students, key=lambda record: record[field_index], reverse=reverse)
        return self._students.copy()

    @staticmethod
    def _resolve_student_field(field: int | str) -> int:
        if isinstance(field, int):
            if 0 <= field < 5:
                return field
            raise ValueError("Индекс поля сортировки вне диапазона.")

        field_map = {
            "id": 0,
            "first_name": 1,
            "second_name": 2,
            "age": 3,
            "sex": 4,
        }
        try:
            return field_map[field]
        except KeyError as exc:
            raise ValueError(f"Неизвестное поле сортировки: {field}.") from exc


class Table:
    def __init__(self, name: str, columns: Iterable[str]) -> None:
        cleaned_columns = [column.strip() for column in columns if column.strip()]
        if not cleaned_columns:
            raise ValueError("Нужно указать хотя бы одну колонку.")
        if len(cleaned_columns) != len(set(cleaned_columns)):
            raise ValueError("Названия колонок должны быть уникальными.")

        self.name = name.strip()
        self._columns = cleaned_columns
        self._records: list[TableRecord] = []

    @property
    def columns(self) -> list[str]:
        return self._columns.copy()

    def create_record(self, values: list[Any]) -> TableRecord:
        if len(values) != len(self._columns):
            raise ValueError(f"Ожидается {len(self._columns)} значений, получено {len(values)}.")
        if any(record[0] == values[0] for record in self._records):
            raise ValueError(f"Запись с id={values[0]} уже существует.")

        record = tuple(value.strip() if isinstance(value, str) else value for value in values)
        self._records.append(record)
        return record

    def select_records(self, filters: list[Any] | None = None) -> list[TableRecord]:
        if not filters:
            return self._records.copy()

        result: list[TableRecord] = []
        for record in self._records:
            matched = True
            for index, filter_value in enumerate(filters):
                if filter_value in (None, ""):
                    continue
                if index >= len(record) or record[index] != filter_value:
                    matched = False
                    break
            if matched:
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
        self._records[record_index] = updated_record
        return updated_record

    def delete_record(self, result: list[TableRecord], n: int = 0) -> bool:
        if not 0 <= n < len(result):
            return False

        try:
            self._records.remove(result[n])
        except ValueError:
            return False
        return True

    def sort_records(self, field: int | str, reverse: bool = False) -> list[TableRecord]:
        field_index = self._resolve_field_index(field)
        self._records = sorted(self._records, key=lambda record: record[field_index], reverse=reverse)
        return self._records.copy()

    def _resolve_field_index(self, field: int | str) -> int:
        if isinstance(field, int):
            if 0 <= field < len(self._columns):
                return field
            raise ValueError("Индекс поля сортировки вне диапазона.")

        try:
            return self._columns.index(field)
        except ValueError as exc:
            raise ValueError(f"Неизвестное поле сортировки: {field}.") from exc


class DatabaseManager:
    def __init__(self) -> None:
        self._tables: list[Table] = []

    def reset(self) -> None:
        self._tables.clear()

    def create_base(self, name: str, columns: list[str]) -> Table:
        table = Table(name, columns)
        self._tables.append(table)
        return table

    def delete_base(self, index: int) -> None:
        del self._tables[index]

    def return_bases(self) -> list[list[Any]]:
        return [[table.name, table.columns, table.select_records()] for table in self._tables]

    def get_tmp(self, number_of_base: int) -> list[str]:
        return self._tables[number_of_base].columns

    def get_table(self, number_of_base: int) -> Table:
        return self._tables[number_of_base]

    def create_record(self, number_of_base: int, values: list[Any]) -> TableRecord:
        return self.get_table(number_of_base).create_record(values)

    def select_records(self, number_of_base: int, filters: list[Any] | None = None) -> list[TableRecord]:
        return self.get_table(number_of_base).select_records(filters)

    def update_record(self, number_of_base: int, record_index: int, new_values: list[Any]) -> TableRecord:
        return self.get_table(number_of_base).update_record(record_index, new_values)

    def delete_record(self, number_of_base: int, result: list[TableRecord], n: int = 0) -> bool:
        return self.get_table(number_of_base).delete_record(result, n)

    def sort_records(
        self,
        number_of_base: int,
        field: int | str,
        reverse: bool = False,
    ) -> list[TableRecord]:
        return self.get_table(number_of_base).sort_records(field, reverse)


database = DatabaseManager()


def create_bs(name: str, temp: list[str]) -> Table:
    return database.create_base(name, temp)


def delete_bs(n: int) -> None:
    database.delete_base(n)


def return_bs() -> list[list[Any]]:
    return database.return_bases()


def get_tmp(number_of_base: int) -> list[str]:
    return database.get_tmp(number_of_base)


def create_rcd(number_of_base: int, values: list[Any]) -> TableRecord:
    return database.create_record(number_of_base, values)


def select_rcd(number_of_base: int, filters: list[Any] | None = None) -> list[TableRecord]:
    return database.select_records(number_of_base, filters)


def update_rcd(number_of_base: int, record_index: int, new_values: list[Any]) -> TableRecord:
    return database.update_record(number_of_base, record_index, new_values)


def delete_rcd(number_of_base: int, result: list[TableRecord], n: int = 0) -> bool:
    return database.delete_record(number_of_base, result, n)


def sort_rcd(number_of_base: int, field: int | str, reverse: bool = False) -> list[TableRecord]:
    return database.sort_records(number_of_base, field, reverse)
