import tempfile
import unittest
from pathlib import Path

from src.db.backend.errors import InvalidStorageDataError, TableNotFoundError
from src.db.backend.file_csv import CsvDatabaseManager
from src.db.backend.file_json import JsonDatabaseManager


class FileDatabaseContractMixin:
    database_class = None
    invalid_file_name = ""

    def create_database(self, directory: str):
        return self.database_class(directory)

    def test_data_is_saved_between_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_db = self.create_database(directory)
            first_db.create_base("students", ["id", "name"], indexed_fields=["id"])
            first_db.create_record(0, ["1", "Ivan"])

            second_db = self.create_database(directory)
            self.assertEqual(second_db.select_records(0), [("1", "Ivan")])
            self.assertEqual(second_db.get_table(0).indexed_fields, ["id"])

    def test_select_with_filters_uses_persisted_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = self.create_database(directory)
            db.create_base("students", ["id", "name"], indexed_fields=["name"])
            db.create_record(0, ["1", "Ivan"])
            db.create_record(0, ["2", "Maria"])

            records = db.select_records(0, [None, "Maria"])

            self.assertEqual(records, [("2", "Maria")])

    def test_select_from_missing_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = self.create_database(directory)

            with self.assertRaises(TableNotFoundError):
                db.select_records(0)

    def test_invalid_storage_data_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid_file = Path(directory) / self.invalid_file_name
            invalid_file.write_text(self.invalid_payload(), encoding="utf-8")

            with self.assertRaises(InvalidStorageDataError):
                self.create_database(directory)

    def invalid_payload(self) -> str:
        raise NotImplementedError


class TestJsonDatabase(FileDatabaseContractMixin, unittest.TestCase):
    database_class = JsonDatabaseManager
    invalid_file_name = "broken.json"

    def invalid_payload(self) -> str:
        return "{broken json"


class TestCsvDatabase(FileDatabaseContractMixin, unittest.TestCase):
    database_class = CsvDatabaseManager
    invalid_file_name = "broken.csv"

    def invalid_payload(self) -> str:
        return "id,name\n1\n"
