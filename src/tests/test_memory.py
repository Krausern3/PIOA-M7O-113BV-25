import io
import unittest

from contextlib import redirect_stdout
from unittest.mock import patch

from src.db.backend.errors import DuplicateIDError, InvalidAgeError
from src.db.backend.memory import (
    DatabaseManager,
    StudentTable,
    Table,
    create_bs,
    create_rcd,
    database,
    delete_bs,
    delete_rcd,
    get_tmp,
    return_bs,
    select_rcd,
    sort_rcd,
    update_rcd,
)
from src.db.tyi import DatabaseCLI
from src.db.tyi import run as tyi_run
from src.db.__main__ import main


class TestStudentTable(unittest.TestCase):
    def setUp(self) -> None:
        self.student_table = StudentTable()

    def test_create_record_and_trim_values(self) -> None:
        record = self.student_table.create_record(1, " John ", " Doe ", 20, " M ")
        self.assertEqual(record, (1, "John", "Doe", 20, "M"))

    def test_create_record_negative_age(self) -> None:
        with self.assertRaises(InvalidAgeError) as context:
            self.student_table.create_record(1, "John", "Doe", -1, "M")
        self.assertEqual(str(context.exception), "Возраст не может быть отрицательным.")

    def test_create_record_duplicate_id(self) -> None:
        self.student_table.create_record(1, "John", "Doe", 20, "M")
        with self.assertRaises(DuplicateIDError) as context:
            self.student_table.create_record(1, "Jane", "Smith", 22, "F")
        self.assertEqual(str(context.exception), "Запись с id=1 уже существует.")

    def test_select_record_with_filters(self) -> None:
        records = [
            (1, "John", "Doe", 20, "M"),
            (2, "Jane", "Smith", 22, "F"),
            (3, "Alice", "Johnson", 20, "F"),
        ]
        for record in records:
            self.student_table.create_record(*record)

        self.assertEqual(self.student_table.select_record(), records)
        self.assertEqual(self.student_table.select_record(age=20), [records[0], records[2]])
        self.assertEqual(self.student_table.select_record(first_name="Jane"), [records[1]])

    def test_sort_records_by_name_and_index(self) -> None:
        self.student_table.create_record(2, "Jane", "Smith", 22, "F")
        self.student_table.create_record(1, "John", "Doe", 20, "M")

        by_id = self.student_table.sort_records(0)
        by_name_desc = self.student_table.sort_records("first_name", reverse=True)

        self.assertEqual(by_id[0][0], 1)
        self.assertEqual(by_name_desc[0][1], "John")

    def test_sort_records_with_invalid_field(self) -> None:
        self.student_table.create_record(1, "John", "Doe", 20, "M")
        with self.assertRaises(ValueError):
            self.student_table.sort_records("unknown")
        with self.assertRaises(ValueError):
            self.student_table.sort_records(10)


class TestTable(unittest.TestCase):
    def setUp(self) -> None:
        self.table = Table("students", ["id", "name", "age"], indexed_fields=["id", "name"])

    def test_create_record_validates_columns_and_duplicate_id(self) -> None:
        self.assertEqual(self.table.create_record(["1", "Alice", "20"]), ("1", "Alice", "20"))
        with self.assertRaises(ValueError):
            self.table.create_record(["1", "Bob", "21"])
        with self.assertRaises(ValueError):
            self.table.create_record(["1", "Bob"])

    def test_table_requires_non_empty_unique_columns(self) -> None:
        with self.assertRaises(ValueError):
            Table("empty", [])
        with self.assertRaises(ValueError):
            Table("duplicate", ["id", "id"])

    def test_select_records_handles_partial_filters(self) -> None:
        self.table.create_record(["1", "Alice", "20"])
        self.table.create_record(["2", "Bob", "21"])
        self.table.create_record(["3", "Alice", "22"])

        self.assertEqual(len(self.table.select_records()), 3)
        self.assertEqual(
            self.table.select_records([None, "Alice", ""]),
            [("1", "Alice", "20"), ("3", "Alice", "22")],
        )

    def test_update_record_updates_only_passed_values(self) -> None:
        self.table.create_record(["1", "Alice", "20"])
        updated = self.table.update_record(0, [None, " Alice Cooper ", None])
        self.assertEqual(updated, ("1", "Alice Cooper", "20"))

    def test_update_record_raises_for_unknown_index(self) -> None:
        with self.assertRaises(ValueError):
            self.table.update_record(0, ["1", "Alice", "20"])

    def test_delete_record_returns_status(self) -> None:
        record = self.table.create_record(["1", "Alice", "20"])
        self.assertTrue(self.table.delete_record([record], 0))
        self.assertFalse(self.table.delete_record([record], 0))
        self.assertFalse(self.table.delete_record([], 0))

    def test_sort_records_by_field_name_and_index(self) -> None:
        self.table.create_record(["3", "Charlie", "19"])
        self.table.create_record(["1", "Alice", "21"])
        self.table.create_record(["2", "Bob", "20"])

        by_name = self.table.sort_records("name")
        by_age_desc = self.table.sort_records(2, reverse=True)

        self.assertEqual([record[1] for record in by_name], ["Alice", "Bob", "Charlie"])
        self.assertEqual([record[2] for record in by_age_desc], ["21", "20", "19"])

    def test_sort_records_raises_for_unknown_field(self) -> None:
        with self.assertRaises(ValueError):
            self.table.sort_records("missing")
        with self.assertRaises(ValueError):
            self.table.sort_records(99)

    def test_indexes_survive_updates_and_deletes(self) -> None:
        self.table.create_record(["1", "Alice", "20"])
        self.table.create_record(["2", "Bob", "21"])
        self.table.update_record(1, [None, "Alice", None])

        self.assertEqual(
            self.table.select_records([None, "Alice", None]),
            [("1", "Alice", "20"), ("2", "Alice", "21")],
        )

        matches = self.table.select_records(["2", None, None])
        self.assertTrue(self.table.delete_record(matches))
        self.assertEqual(self.table.select_records([None, "Alice", None]), [("1", "Alice", "20")])


class TestDatabaseManagerAndModuleAPI(unittest.TestCase):
    def setUp(self) -> None:
        database.reset()
        self.manager = DatabaseManager()

    def tearDown(self) -> None:
        database.reset()

    def test_database_manager_crud_and_sort(self) -> None:
        table = self.manager.create_base("students", ["id", "name", "age"], indexed_fields=["id", "name"])
        self.assertEqual(table.columns, ["id", "name", "age"])
        self.assertEqual(table.indexed_fields, ["id", "name"])

        self.manager.create_record(0, ["2", "Bob", "21"])
        self.manager.create_record(0, ["1", "Alice", "20"])

        self.assertEqual(self.manager.select_records(0, [None, "Alice", None]), [("1", "Alice", "20")])
        self.assertEqual(self.manager.sort_records(0, "id"), [("1", "Alice", "20"), ("2", "Bob", "21")])

        updated = self.manager.update_record(0, 1, [None, " Bobby ", None])
        self.assertEqual(updated, ("2", "Bobby", "21"))

        self.assertTrue(self.manager.delete_record(0, [("1", "Alice", "20")], 0))
        self.assertEqual(self.manager.return_bases(), [["students", ["id", "name", "age"], [("2", "Bobby", "21")]]])

        self.manager.reset()
        self.assertEqual(self.manager.return_bases(), [])

    def test_module_level_wrappers_follow_same_behavior(self) -> None:
        create_bs("students", ["id", "name", "age"], indexed_fields=["id"])
        self.assertEqual(get_tmp(0), ["id", "name", "age"])

        create_rcd(0, ["2", "Bob", "21"])
        create_rcd(0, ["1", "Alice", "20"])

        self.assertEqual(select_rcd(0), [("2", "Bob", "21"), ("1", "Alice", "20")])
        self.assertEqual(sort_rcd(0, "name"), [("1", "Alice", "20"), ("2", "Bob", "21")])

        update_rcd(0, 1, [None, " Bobby ", None])
        self.assertEqual(select_rcd(0), [("1", "Alice", "20"), ("2", "Bobby", "21")])

        self.assertTrue(delete_rcd(0, [("1", "Alice", "20")], 0))
        self.assertEqual(return_bs(), [["students", ["id", "name", "age"], [("2", "Bobby", "21")]]])

        delete_bs(0)
        self.assertEqual(return_bs(), [])


class TestDatabaseCLI(unittest.TestCase):
    """
    Тесты консольного интерфейса (src/db/tyi.py).

    DatabaseCLI управляется через input(), поэтому вместо реального
    ввода подставляем заранее заготовленную очередь ответов
    (unittest.mock.patch с side_effect). После run() проверяем
    состояние самой базы данных (cli.database) — так тесты не зависят
    от точного текста сообщений, которые печатает CLI.
    """

    @staticmethod
    def _run_scenario(inputs: list[str]) -> DatabaseCLI:
        with patch("builtins.input", side_effect=inputs):
            cli = DatabaseCLI()
            cli.run()
        return cli

    def test_choose_database_dispatches_by_user_choice(self) -> None:
        with patch("src.db.tyi.JsonDatabaseManager") as mock_json, \
             patch("src.db.tyi.CsvDatabaseManager") as mock_csv:
            with patch("builtins.input", side_effect=["2"]):
                DatabaseCLI()
            mock_json.assert_called_once_with("data/json")

            with patch("builtins.input", side_effect=["3"]):
                DatabaseCLI()
            mock_csv.assert_called_once_with("data/csv")

        cli = self._run_scenario(["1", "0"])
        self.assertIsInstance(cli.database, DatabaseManager)

    def test_create_table_and_add_record(self) -> None:
        inputs = ["1", "1", "students", "id,name", "", "0"]
        cli = self._run_scenario(inputs)
        self.assertEqual(cli.database.get_tmp(0), ["id", "name"])

    def test_duplicate_id_is_rejected(self) -> None:
        inputs = [
            "1",
            "1", "students", "id,name", "",
            "2", "0",
            "1", "1", "Иван",   # добавить запись
            "1", "1", "Мария",  # дубликат id -> не добавится
            "0", "0",
        ]
        cli = self._run_scenario(inputs)
        self.assertEqual(cli.database.select_records(0), [("1", "Иван")])

    def test_update_and_delete_record(self) -> None:
        inputs = [
            "1",
            "1", "students", "id,name", "",
            "2", "0",
            "1", "1", "Иван",
            "3", "", "", "1", "", "Пётр",  # найти -> обновить имя
            "3", "", "", "2",              # найти -> удалить
            "0", "0",
        ]
        cli = self._run_scenario(inputs)
        self.assertEqual(cli.database.select_records(0), [])

    def test_sort_and_index_do_not_crash(self) -> None:
        inputs = [
            "1",
            "1", "students", "id,name", "",
            "2", "0",
            "1", "2", "Боб",
            "1", "1", "Аня",
            "4", "name", "asc",
            "5", "",
            "0", "0",
        ]
        cli = self._run_scenario(inputs)
        self.assertEqual(
            [record[1] for record in cli.database.select_records(0)],
            ["Аня", "Боб"],
        )

    def test_delete_base(self) -> None:
        inputs = ["1", "1", "students", "id", "", "3", "0", "0"]
        cli = self._run_scenario(inputs)
        self.assertEqual(cli.database.return_bases(), [])

    def test_open_base_with_no_tables_and_out_of_range(self) -> None:
        # проверяем только, что программа не падает
        self._run_scenario(["1", "2", "0"])
        self._run_scenario(["1", "1", "students", "id", "", "2", "5", "0"])
        self._run_scenario(["1", "1", "students", "id", "", "2", "-1", "0"])

    def test_unknown_commands_do_not_crash(self) -> None:
        self._run_scenario(["1", "9", "0"])
        inputs = ["1", "1", "students", "id", "", "2", "0", "9", "0", "0"]
        self._run_scenario(inputs)

    def test_delete_base_without_tables_and_out_of_range(self) -> None:
        self._run_scenario(["1", "3", "0"])
        inputs = ["1", "1", "students", "id", "", "3", "5", "0"]
        self._run_scenario(inputs)

    def test_create_base_with_empty_name_does_not_crash(self) -> None:
        inputs = ["1", "1", "", "id", "", "0"]
        cli = self._run_scenario(inputs)
        self.assertEqual(cli.database.return_bases(), [])

    def test_module_level_run_delegates_to_cli(self) -> None:
        with patch("builtins.input", side_effect=["1", "0"]):
            tyi_run()

    def test_main_entrypoint_calls_run(self) -> None:
        with patch("src.db.__main__.run") as mock_run:
            main()
        mock_run.assert_called_once()
