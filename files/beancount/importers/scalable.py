"""Beancount importer for Scalable Capital Germany CSV exports."""

import csv
from datetime import datetime
from pathlib import Path

from beangulp import Importer
from beancount.core import amount, data
from beancount.core.number import D


class ScalableCapitalImporter(Importer):
    """Importer for Scalable Capital Germany CSV exports.

    Scalable Capital export format typically includes:
    Datum,Typ,ISIN,Name,Stück,Kurs,Betrag,Gebühren,Währung
    (Date,Type,ISIN,Name,Quantity,Price,Amount,Fees,Currency)
    """

    def __init__(
        self,
        cash_account: str,
        investment_account_prefix: str = "Assets:Investments:Scalable",
        fees_account: str = "Expenses:Investment:Fees",
        currency: str = "EUR",
    ):
        self.cash_account = cash_account
        self.investment_account_prefix = investment_account_prefix
        self.fees_account = fees_account
        self.currency = currency

    def identify(self, filepath: Path) -> bool:
        if not filepath.suffix.lower() == ".csv":
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                header = f.readline().strip().lower()
                return "scalable" in filepath.name.lower() or (
                    "isin" in header and ("stück" in header or "stuck" in header)
                )
        except (IOError, UnicodeDecodeError):
            return False

    def filename(self, filepath: Path) -> str:
        return f"scalable.{filepath.name}"

    def account(self, filepath: Path) -> str:
        return self.cash_account

    def extract(self, filepath: Path, existing_entries=None):
        entries = []

        with open(filepath, "r", encoding="utf-8") as f:
            # Try different delimiters (German CSVs often use semicolon)
            content = f.read()
            f.seek(0)

            delimiter = ";" if ";" in content.split("\n")[0] else ","
            reader = csv.DictReader(f, delimiter=delimiter)

            for index, row in enumerate(reader):
                try:
                    # Handle German date format
                    date_str = row.get("Datum", row.get("Date", ""))
                    for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue

                    # Get ISIN or symbol
                    isin = row.get("ISIN", "").strip()
                    name = row.get("Name", row.get("Wertpapier", "")).strip()
                    symbol = isin if isin else name.replace(" ", "_")[:10]

                    trade_type = row.get("Typ", row.get("Type", "")).strip().upper()

                    # Handle German number format (comma as decimal separator)
                    def parse_german_number(s):
                        if not s:
                            return D("0")
                        return D(s.replace(".", "").replace(",", ".").replace("€", "").strip())

                    quantity = parse_german_number(row.get("Stück", row.get("Quantity", "0")))
                    price = parse_german_number(row.get("Kurs", row.get("Price", "0")))
                    total = parse_german_number(row.get("Betrag", row.get("Amount", "0")))
                    fees = parse_german_number(row.get("Gebühren", row.get("Fees", "0")))

                    currency = row.get("Währung", row.get("Currency", self.currency)).strip()
                    if not currency:
                        currency = self.currency

                    meta = data.new_metadata(str(filepath), index)

                    postings = []

                    if trade_type in ["KAUF", "BUY", "SPARPLAN"]:
                        postings.append(
                            data.Posting(
                                f"{self.investment_account_prefix}:{symbol}",
                                amount.Amount(quantity, symbol),
                                data.Cost(price, currency, date, None),
                                None,
                                None,
                                None,
                            )
                        )
                        if fees > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(fees, currency),
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                        postings.append(
                            data.Posting(
                                self.cash_account,
                                amount.Amount(-abs(total), currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        narration = f"Kauf {quantity} {name or symbol}"

                    elif trade_type in ["VERKAUF", "SELL"]:
                        postings.append(
                            data.Posting(
                                f"{self.investment_account_prefix}:{symbol}",
                                amount.Amount(-quantity, symbol),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        if fees > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(fees, currency),
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                        postings.append(
                            data.Posting(
                                self.cash_account,
                                amount.Amount(abs(total), currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        narration = f"Verkauf {quantity} {name or symbol}"

                    elif trade_type in ["DIVIDENDE", "DIVIDEND"]:
                        postings.append(
                            data.Posting(
                                self.cash_account,
                                amount.Amount(abs(total), currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        postings.append(
                            data.Posting(
                                f"Income:Dividends:{symbol}",
                                amount.Amount(-abs(total), currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        narration = f"Dividende {name or symbol}"
                    else:
                        continue

                    txn = data.Transaction(
                        meta=meta,
                        date=date,
                        flag="*",
                        payee="Scalable Capital",
                        narration=narration,
                        tags=frozenset(),
                        links=frozenset(),
                        postings=postings,
                    )
                    entries.append(txn)
                except (KeyError, ValueError):
                    continue

        return entries
