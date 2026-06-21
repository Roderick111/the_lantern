"""Persistence-layer exceptions."""


class StaleStateError(Exception):
    """Raised when a save conflicts with a newer revision in the database."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Stale save: expected revision {expected}, found {actual}")