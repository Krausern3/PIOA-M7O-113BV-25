class StudentTableError(Exception):
    """Base class for StudentTable-related errors."""


class InvalidAgeError(StudentTableError):
    """Raised when a student age is invalid."""


class DuplicateIDError(StudentTableError):
    """Raised when a record with the same identifier already exists."""


class TableAlreadyExistsError(Exception):
    """Raised when a table with the same name already exists."""


class TableNotFoundError(Exception):
    """Raised when a table cannot be found."""


class InvalidStorageDataError(Exception):
    """Raised when persisted table data has an invalid structure."""
