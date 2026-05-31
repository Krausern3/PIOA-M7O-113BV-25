from __future__ import annotations

from .backend.memory import (
    create_bs,
    create_rcd,
    delete_bs,
    delete_rcd,
    get_tmp,
    return_bs,
    select_rcd,
    sort_rcd,
    update_rcd,
)


class DatabaseCLI:
    def __init__(self) -> None:
        self._table_actions = {
            "1": self._add_record,
            "2": self._show_all_records,
            "3": self._find_records,
            "4": self._sort_records,
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

    def _create_base(self) -> None:
        name = input("Введите название для базы: ").strip()
        columns_input = input("Введите имена колонок через запятую: ").strip()
        columns = [column.strip() for column in columns_input.split(",")]
        try:
            create_bs(name, columns)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        print(f"База '{name}' создана с колонками: {get_tmp(len(return_bs()) - 1)}")

    def _open_base(self) -> None:
        bases = return_bs()
        self._show_bases(bases)
        if not bases:
            return

        base_index = self._read_int("Выберите базу (-1 для выхода): ", allow_empty=False, min_value=-1)
        if base_index == -1:
            return
        if base_index >= len(bases):
            print("Ошибка: базы с таким номером нет.")
            return

        columns = get_tmp(base_index)
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
        bases = return_bs()
        self._show_bases(bases)
        if not bases:
            print("Баз для удаления нет.")
            return

        base_index = self._read_int("Введите номер базы для удаления: ", allow_empty=False, min_value=0)
        if base_index >= len(bases):
            print("Ошибка: базы с таким номером нет.")
            return
        delete_bs(base_index)
        print("База удалена.")

    def _add_record(self, base_index: int, columns: list[str]) -> None:
        values = [input(f"{column}: ").strip() for column in columns]
        try:
            record = create_rcd(base_index, values)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        print(f"Запись добавлена: {record}")

    def _show_all_records(self, base_index: int, _: list[str]) -> None:
        self._print_records(select_rcd(base_index))

    def _find_records(self, base_index: int, columns: list[str]) -> None:
        filters = []
        print("Введите фильтры (Enter = пропустить поле):")
        for column in columns:
            value = input(f"{column}: ").strip()
            filters.append(value or None)

        records = select_rcd(base_index, filters)
        self._print_records(records, numbered=True)
        if not records:
            return

        action = input("1. Обновить 2. Удалить 0. Назад: ").strip()
        if action == "1":
            self._update_record(base_index, records, columns)
        elif action == "2":
            self._delete_record(base_index, records)

    def _sort_records(self, base_index: int, columns: list[str]) -> None:
        print(f"Поля сортировки: {', '.join(columns)}")
        field = input("Введите имя поля или его индекс: ").strip()
        reverse = input("Порядок (asc/desc): ").strip().lower() == "desc"
        try:
            field_value: int | str = int(field) if field.isdigit() else field
            records = sort_rcd(base_index, field_value, reverse=reverse)
        except ValueError as exc:
            print(f"Ошибка: {exc}")
            return
        self._print_records(records)

    def _update_record(self, base_index: int, records: list[tuple], columns: list[str]) -> None:
        record_index = self._choose_record(records)
        if record_index is None:
            return

        current_record = records[record_index]
        new_values = []
        for index, column in enumerate(columns):
            value = input(f"{column} (текущее: {current_record[index]}): ").strip()
            new_values.append(value or None)

        if all(value is None for value in new_values):
            print("Нет изменений для сохранения.")
            return

        all_records = select_rcd(base_index)
        actual_index = all_records.index(current_record)
        update_rcd(base_index, actual_index, new_values)
        print("Данные успешно изменены.")

    def _delete_record(self, base_index: int, records: list[tuple]) -> None:
        record_index = self._choose_record(records)
        if record_index is None:
            return
        if delete_rcd(base_index, records, record_index):
            print("Запись удалена.")
            return
        print("Ошибка: не удалось удалить запись.")

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
            print("Нет доступных баз.")
            return
        for index, base in enumerate(bases):
            print(f"{index}. {base[0]} (колонки: {base[1]})")

    @staticmethod
    def _print_base_menu() -> None:
        print("\n<> Система управления базами <>")
        print("1. Создать новую таблицу")
        print("2. Открыть таблицу")
        print("3. Удалить таблицу")
        print("0. Выход")

    @staticmethod
    def _print_table_menu() -> None:
        print("\n=== Таблица ===")
        print("1. Добавить запись")
        print("2. Показать все записи")
        print("3. Найти записи по фильтру")
        print("4. Сортировать записи")
        print("0. Назад")


def run() -> None:
    DatabaseCLI().run()
