from __future__ import annotations

from typing import Any

from .database import DatabaseManager as BaseDatabaseManager
from .errors import DuplicateIDError, InvalidAgeError
from .table import Table, TableRecord

type StudentRecord = tuple[int, str, str, int, str]


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
            raise InvalidAgeError("Возраст не может быть отрицательным.")
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


class MemoryDatabaseManager(BaseDatabaseManager):
    def __init__(self) -> None:
        super().__init__()


DatabaseManager = MemoryDatabaseManager
database = MemoryDatabaseManager()


def create_bs(name: str, temp: list[str], indexed_fields: list[str] | None = None) -> Table:
    return database.create_base(name, temp, indexed_fields=indexed_fields)


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
