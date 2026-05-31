import unittest

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


class TestStudentTable(unittest.TestCase):
    def setUp(self):
        self.student_table = StudentTable()

    def test_create_record_and_trim_values(self):
        record = self.student_table.create_record(1, " John ", " Doe ", 20, " M ")
        self.assertEqual(record, (1, "John", "Doe", 20, "M"))

    def test_create_record_negative_age(self):
        with self.assertRaises(InvalidAgeError) as context:
            self.student_table.create_record(1, "John", "Doe", -1, "M")
        self.assertEqual(str(context.exception), "Поле age не может быть отрицательным.")

    def test_create_record_duplicate_id(self):
        self.student_table.create_record(1, "John", "Doe", 20, "M")
        with self.assertRaises(DuplicateIDError) as context:
            self.student_table.create_record(1, "Jane", "Smith", 22, "F")
        self.assertEqual(str(context.exception), "Запись с id=1 уже существует.")

    def test_select_record_with_filters(self):
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

    def test_sort_records_by_name_and_index(self):
        self.student_table.create_record(2, "Jane", "Smith", 22, "F")
        self.student_table.create_record(1, "John", "Doe", 20, "M")

        by_id = self.student_table.sort_records(0)
        by_name_desc = self.student_table.sort_records("first_name", reverse=True)

        self.assertEqual(by_id[0][0], 1)
        self.assertEqual(by_name_desc[0][1], "John")

    def test_sort_records_with_invalid_field(self):
        self.student_table.create_record(1, "John", "Doe", 20, "M")
        with self.assertRaises(ValueError):
            self.student_table.sort_records("unknown")
        with self.assertRaises(ValueError):
            self.student_table.sort_records(10)


class TestTable(unittest.TestCase):
    def setUp(self):
        self.table = Table("students", ["id", "name", "age"])

    def test_create_record_validates_columns_and_duplicate_id(self):
        self.assertEqual(self.table.create_record(["1", "Alice", "20"]), ("1", "Alice", "20"))
        with self.assertRaises(ValueError):
            self.table.create_record(["1", "Bob", "21"])
        with self.assertRaises(ValueError):
            self.table.create_record(["1", "Bob"])

    def test_table_requires_non_empty_unique_columns(self):
        with self.assertRaises(ValueError):
            Table("empty", [])
        with self.assertRaises(ValueError):
            Table("duplicate", ["id", "id"])

    def test_select_records_handles_partial_filters(self):
        self.table.create_record(["1", "Alice", "20"])
        self.table.create_record(["2", "Bob", "21"])
        self.table.create_record(["3", "Alice", "22"])

        self.assertEqual(len(self.table.select_records()), 3)
        self.assertEqual(
            self.table.select_records([None, "Alice", ""]),
            [("1", "Alice", "20"), ("3", "Alice", "22")],
        )

    def test_update_record_updates_only_passed_values(self):
        self.table.create_record(["1", "Alice", "20"])
        updated = self.table.update_record(0, [None, " Alice Cooper ", None])
        self.assertEqual(updated, ("1", "Alice Cooper", "20"))

    def test_update_record_raises_for_unknown_index(self):
        with self.assertRaises(ValueError):
            self.table.update_record(0, ["1", "Alice", "20"])

    def test_delete_record_returns_status(self):
        record = self.table.create_record(["1", "Alice", "20"])
        self.assertTrue(self.table.delete_record([record], 0))
        self.assertFalse(self.table.delete_record([record], 0))
        self.assertFalse(self.table.delete_record([], 0))

    def test_sort_records_by_field_name_and_index(self):
        self.table.create_record(["3", "Charlie", "19"])
        self.table.create_record(["1", "Alice", "21"])
        self.table.create_record(["2", "Bob", "20"])

        by_name = self.table.sort_records("name")
        by_age_desc = self.table.sort_records(2, reverse=True)

        self.assertEqual([record[1] for record in by_name], ["Alice", "Bob", "Charlie"])
        self.assertEqual([record[2] for record in by_age_desc], ["21", "20", "19"])

    def test_sort_records_raises_for_unknown_field(self):
        with self.assertRaises(ValueError):
            self.table.sort_records("missing")
        with self.assertRaises(ValueError):
            self.table.sort_records(99)


class TestDatabaseManagerAndModuleAPI(unittest.TestCase):
    def setUp(self):
        database.reset()
        self.manager = DatabaseManager()

    def tearDown(self):
        database.reset()

    def test_database_manager_crud_and_sort(self):
        table = self.manager.create_base("students", ["id", "name", "age"])
        self.assertEqual(table.columns, ["id", "name", "age"])

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

    def test_module_level_wrappers_follow_same_behavior(self):
        create_bs("students", ["id", "name", "age"])
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
