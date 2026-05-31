from __future__ import annotations

from .backend.database import DatabaseManager
from .backend.file_csv import CsvDatabaseManager
from .backend.file_json import JsonDatabaseManager
from .backend.memory import MemoryDatabaseManager


class DatabaseCLI:
    def __init__(self) -> None:
        self.database = self._choose_database()
        self._table_actions = {
            "1": self._add_record,
            "2": self._show_all_records,
            "3": self._find_records,
            "4": self._sort_records,
            "5": self._configure_indexes,
        }

    def run(self) -> None:
        while True:
            self._print_base_menu()
            action = input("Выберите действие: ").strip()
            if action == "1":
                self._create_base()
            elif action == "2":
                self._open_base()
            elif action == "3":
                self._delete_base()
            elif action == "0":
                return
            else:
                print("Неизвестная команда. Повторите ввод.")

    def _choose_database(self) -> DatabaseManager:
        print("Выберите тип базы данных:")
        print("1. In-memory")
        print("2. Файловая база (JSON)")
        print("3. Файловая база (CSV)")

        choice = input("Введите номер: ").strip()
        if choice == "2":
            return JsonDatabaseManager("data/json")
        if choice == "3":
            return CsvDatabaseManager("data/csv")
        return MemoryDatabaseManager()

    def _create_base(self) -> None:
        name = input("Введите имя таблицы: ").strip()
        columns_input = input("Введите имена столбцов через запятую: ").strip()
        columns = [column.strip() for column in columns_input.split(",")]
        indexed_fields = self._read_indexed_fields(columns)
        try:
            table = self.database.create_base(name, columns, indexed_fields=indexed_fields)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        print(
            f"Таблица '{table.name}' создана со столбцами {table.columns} "
            f"и индексами {table.indexed_fields}."
        )

    def _open_base(self) -> None:
        bases = self.database.return_bases()
        self._show_bases(bases)
        if not bases:
            return

        base_index = self._read_int("Выберите таблицу (-1 для выхода): ", allow_empty=False, min_value=-1)
        if base_index == -1:
            return
        if base_index >= len(bases):
            print("Ошибка: таблицы с таким номером нет.")
            return

        columns = self.database.get_tmp(base_index)
        while True:
            self._print_table_menu()
            action = input("Выберите действие: ").strip()
            if action == "0":
                return

            handler = self._table_actions.get(action)
            if handler is None:
                print("Неизвестная команда. Повторите ввод.")
                continue
            handler(base_index, columns)

    def _delete_base(self) -> None:
        bases = self.database.return_bases()
        self._show_bases(bases)
        if not bases:
            print("Нет таблиц для удаления.")
            return

        base_index = self._read_int("Введите номер таблицы для удаления: ", allow_empty=False, min_value=0)
        if base_index >= len(bases):
            print("Ошибка: таблицы с таким номером нет.")
            return
        self.database.delete_base(base_index)
        print("Таблица удалена.")

    def _add_record(self, base_index: int, columns: list[str]) -> None:
        values = [input(f"{column}: ").strip() for column in columns]
        try:
            record = self.database.create_record(base_index, values)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        print(f"Запись добавлена: {record}")

    def _show_all_records(self, base_index: int, _: list[str]) -> None:
        self._print_records(self.database.select_records(base_index))

    def _find_records(self, base_index: int, columns: list[str]) -> None:
        filters = []
        print("Введите фильтры (Enter = пропустить поле):")
        for column in columns:
            value = input(f"{column}: ").strip()
            filters.append(value or None)

        records = self.database.select_records(base_index, filters)
        self._print_records(records, numbered=True)
        if not records:
            return

        action = input("1. Обновить 2. Удалить 0. Назад: ").strip()
        if action == "1":
            self._update_record(base_index, records, columns)
        elif action == "2":
            self._delete_record(base_index, records)

    def _sort_records(self, base_index: int, columns: list[str]) -> None:
        print(f"Поля для сортировки: {', '.join(columns)}")
        field = input("Введите имя поля или его индекс: ").strip()
        reverse = input("Порядок (asc/desc): ").strip().lower() == "desc"
        try:
            field_value: int | str = int(field) if field.isdigit() else field
            records = self.database.sort_records(base_index, field_value, reverse=reverse)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        self._print_records(records)

    def _configure_indexes(self, base_index: int, columns: list[str]) -> None:
        print(f"Доступные поля: {', '.join(columns)}")
        indexed_fields = self._read_indexed_fields(columns)
        try:
            fields = self.database.create_index(base_index, indexed_fields or columns)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        print(f"Индексы обновлены: {fields}")

    def _update_record(self, base_index: int, records: list[tuple], columns: list[str]) -> None:
        record_index = self._choose_record(records)
        if record_index is None:
            return

        current_record = records[record_index]
        new_values = []
        for index, column in enumerate(columns):
            value = input(f"{column} (текущее значение: {current_record[index]}): ").strip()
            new_values.append(value or None)

        if all(value is None for value in new_values):
            print("Нет изменений для сохранения.")
            return

        all_records = self.database.select_records(base_index)
        actual_index = all_records.index(current_record)
        self.database.update_record(base_index, actual_index, new_values)
        print("Запись обновлена.")

    def _delete_record(self, base_index: int, records: list[tuple]) -> None:
        record_index = self._choose_record(records)
        if record_index is None:
            return
        if self.database.delete_record(base_index, records, record_index):
            print("Запись удалена.")
            return
        print("Ошибка: не удалось удалить запись.")

    @staticmethod
    def _read_indexed_fields(columns: list[str]) -> list[str]:
        raw = input(
            "Введите поля для индексации через запятую "
            "(Enter = индексировать все столбцы): "
        ).strip()
        if not raw:
            return columns.copy()
        return [field.strip() for field in raw.split(",") if field.strip()]

    @staticmethod
    def _choose_record(records: list[tuple]) -> int | None:
        if len(records) == 1:
            return 0

        choice = input("Выберите номер записи: ").strip()
        if not choice.isdigit():
            print("Ошибка: введите целое число.")
            return None
        index = int(choice)
        if not 0 <= index < len(records):
            print("Ошибка: записи с таким номером нет.")
            return None
        return index

    @staticmethod
    def _read_int(prompt: str, allow_empty: bool, min_value: int) -> int | None:
        while True:
            raw = input(prompt).strip()
            if allow_empty and raw == "":
                return None
            try:
                value = int(raw)
            except ValueError:
                print("Ошибка: введите целое число.")
                continue
            if value < min_value:
                print("Ошибка: число меньше допустимого.")
                continue
            return value

    @staticmethod
    def _print_records(records: list[tuple], numbered: bool = False) -> None:
        if not records:
            print("Записи не найдены.")
            return

        for index, record in enumerate(records):
            prefix = f"{index}. " if numbered else ""
            print(f"{prefix}{record}")

    @staticmethod
    def _show_bases(bases: list[list]) -> None:
        if not bases:
            print("Нет доступных таблиц.")
            return
        for index, base in enumerate(bases):
            print(f"{index}. {base[0]} (столбцы: {base[1]})")

    @staticmethod
    def _print_base_menu() -> None:
        print("\n<> Система управления базами <>")
        print("1. Создать таблицу")
        print("2. Открыть таблицу")
        print("3. Удалить таблицу")
        print("0. Выход")

    @staticmethod
    def _print_table_menu() -> None:
        print("\n=== Таблица ===")
        print("1. Добавить запись")
        print("2. Показать все записи")
        print("3. Найти записи")
        print("4. Отсортировать записи")
        print("5. Настроить индексы")
        print("0. Назад")


def run() -> None:
    DatabaseCLI().run()
