"""Generic repository: wraps a CsvTable and converts rows <-> model objects."""
from __future__ import annotations

from typing import Generic, TypeVar

from app.database.csv_table import CsvTable

T = TypeVar("T")


class Repository(Generic[T]):
    def __init__(self, table: CsvTable, model_cls: type[T]):
        self.table = table
        self.model_cls = model_cls

    def all(self) -> list[T]:
        return [self.model_cls.from_row(r) for r in self.table.all()]

    def get(self, id_value) -> T | None:
        row = self.table.get(id_value)
        return self.model_cls.from_row(row) if row else None

    def find(self, **criteria) -> list[T]:
        return [self.model_cls.from_row(r) for r in self.table.find(**criteria)]

    def add(self, model: T) -> T:
        row = self.table.insert(model.to_row())
        return self.model_cls.from_row(row)

    def update(self, id_value, changes: dict) -> T | None:
        row = self.table.update(id_value, changes)
        return self.model_cls.from_row(row) if row else None
