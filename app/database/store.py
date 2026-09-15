"""Database: the single object that owns every repository/CSV table."""
from __future__ import annotations

from pathlib import Path

from app.database.csv_table import CsvTable
from app.database.repository import Repository
from app.models import Case, Garage, Policyholder, Sms


class Database:
    def __init__(self, data_dir: str | Path):
        data_dir = Path(data_dir)
        self.policyholders = Repository(
            CsvTable(data_dir / "policyholders.csv", Policyholder.FIELDS), Policyholder
        )
        self.garages = Repository(
            CsvTable(data_dir / "garages.csv", Garage.FIELDS), Garage
        )
        self.cases = Repository(CsvTable(data_dir / "cases.csv", Case.FIELDS), Case)
        self.sms = Repository(CsvTable(data_dir / "sms.csv", Sms.FIELDS), Sms)
