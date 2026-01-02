"""Beancount importer for Commonwealth Bank Australia CSV exports."""

import csv
import re
from datetime import datetime
from pathlib import Path

from beangulp import Importer
from beancount.core import amount, data
from beancount.core.number import D


class CommBankImporter(Importer):
    """Importer for Commonwealth Bank Australia CSV statements.

    CommBank CSV format:
    Date,Amount,Description,Balance
    01/01/2024,-50.00,"DIRECT DEBIT",1000.00
    """

    def __init__(self, account: str, currency: str = "AUD"):
        self.account = account
        self.currency = currency

    def identify(self, filepath: Path) -> bool:
        if not filepath.suffix.lower() == ".csv":
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.readline().strip()
                # CommBank CSVs typically start with Date,Amount,Description,Balance
                return "Date" in header and "Amount" in header and "Balance" in header
        except (IOError, UnicodeDecodeError):
            return False

    def filename(self, filepath: Path) -> str:
        return f"commbank.{filepath.name}"

    def account(self, filepath: Path) -> str:
        return self.account

    def extract(self, filepath: Path, existing_entries=None):
        entries = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for index, row in enumerate(reader):
                try:
                    # Parse date (DD/MM/YYYY format)
                    date = datetime.strptime(row["Date"], "%d/%m/%Y").date()

                    # Parse amount
                    amt = D(row["Amount"].replace(",", ""))

                    # Description/narration
                    narration = row.get("Description", "").strip()

                    meta = data.new_metadata(str(filepath), index)

                    txn = data.Transaction(
                        meta=meta,
                        date=date,
                        flag="*",
                        payee=None,
                        narration=narration,
                        tags=frozenset(),
                        links=frozenset(),
                        postings=[
                            data.Posting(
                                self.account,
                                amount.Amount(amt, self.currency),
                                None,
                                None,
                                None,
                                None,
                            ),
                        ],
                    )
                    entries.append(txn)
                except (KeyError, ValueError) as e:
                    continue

        return entries
