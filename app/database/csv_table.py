"""A single CSV file exposed as a tiny table of string rows.

Everything is stored as strings; typed conversion is the model's job. A process
level lock guards writes so concurrent requests don't corrupt the file.
"""
from __future__ import annotations

import csv
from pathlib import Path
from threading import Lock


class CsvTable:
    def __init__(self, path: str | Path, fieldnames: list[str], id_field: str | None = "id"):
        self.path = Path(path)
        self.fieldnames = list(fieldnames)
        self.id_field = id_field
        self._lock = Lock()
        if not self.path.exists():
            self._write_all([])

    def _read_all(self) -> list[dict]:
        with self.path.open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write_all(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {k: ("" if row.get(k) is None else row.get(k)) for k in self.fieldnames}
                )

    def all(self) -> list[dict]:
        return self._read_all()

    def get(self, id_value) -> dict | None:
        if self.id_field is None:
            raise ValueError("get() requires an id_field")
        target = str(id_value)
        for row in self._read_all():
            if row.get(self.id_field) == target:
                return row
        return None

    def find(self, **criteria) -> list[dict]:
        rows = self._read_all()
        return [
            row
            for row in rows
            if all(str(row.get(k)) == str(v) for k, v in criteria.items())
        ]

    def insert(self, row: dict) -> dict:
        with self._lock:
            rows = self._read_all()
            row = dict(row)
            if self.id_field and not row.get(self.id_field):
                row[self.id_field] = self._next_id(rows)
            rows.append({k: row.get(k) for k in self.fieldnames})
            self._write_all(rows)
            return row

    def update(self, id_value, changes: dict) -> dict | None:
        if self.id_field is None:
            raise ValueError("update() requires an id_field")
        with self._lock:
            rows = self._read_all()
            target = str(id_value)
            updated = None
            for row in rows:
                if row.get(self.id_field) == target:
                    for k, v in changes.items():
                        if k in self.fieldnames:
                            row[k] = "" if v is None else v
                    updated = row
            if updated is not None:
                self._write_all(rows)
            return updated

    def _next_id(self, rows: list[dict]) -> int:
        ids = [int(r[self.id_field]) for r in rows if r.get(self.id_field)]
        return max(ids) + 1 if ids else 1
