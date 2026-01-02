"""Beancount importer for ubank (formerly 86 400) Australia CSV exports."""

import csv
from datetime import datetime
from pathlib import Path

from beangulp import Importer
from beancount.core import amount, data
from beancount.core.number import D


class UBankImporter(Importer):
    """Importer for ubank Australia CSV statements.

    ubank CSV format (may vary):
    Date,Description,Debit,Credit,Balance
    2024-01-01,Transfer,-100.00,,900.00
    """

    def __init__(self, account: str, currency: str = "AUD"):
        self.account = account
        self.currency = currency

    def identify(self, filepath: Path) -> bool:
        if not filepath.suffix.lower() == ".csv":
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.readline().strip().lower()
                # Check for ubank-specific patterns
                return "ubank" in filepath.name.lower() or (
                    "date" in header and ("debit" in header or "credit" in header)
                )
        except (IOError, UnicodeDecodeError):
            return False

    def filename(self, filepath: Path) -> str:
        return f"ubank.{filepath.name}"

    def account(self, filepath: Path) -> str:
        return self.account

    def extract(self, filepath: Path, existing_entries=None):
        entries = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for index, row in enumerate(reader):
                try:
                    # Try multiple date formats
                    date_str = row.get("Date", "")
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                        try:
                            date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue

                    # Calculate amount from Debit/Credit columns
                    debit = row.get("Debit", "").replace(",", "").replace("$", "")
                    credit = row.get("Credit", "").replace(",", "").replace("$", "")

                    if debit and debit != "":
                        amt = -D(debit)
                    elif credit and credit != "":
                        amt = D(credit)
                    else:
                        # Try single Amount column
                        amt_str = row.get("Amount", "0").replace(",", "").replace("$", "")
                        amt = D(amt_str)

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
                except (KeyError, ValueError):
                    continue

        return entries
