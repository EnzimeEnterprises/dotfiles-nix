"""Beancount importer for SelfWealth Australia CSV exports."""

import csv
from datetime import datetime
from pathlib import Path

from beangulp import Importer
from beancount.core import amount, data
from beancount.core.number import D


class SelfWealthImporter(Importer):
    """Importer for SelfWealth Australia investment platform CSV exports.

    SelfWealth export format typically includes:
    Trade Date,Settlement Date,Type,Code,Company,Quantity,Price,Brokerage,GST,Total
    """

    def __init__(
        self,
        cash_account: str,
        investment_account_prefix: str = "Assets:Investments:SelfWealth",
        fees_account: str = "Expenses:Investment:Brokerage",
        currency: str = "AUD",
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
                return "selfwealth" in filepath.name.lower() or (
                    "trade date" in header and "code" in header and "brokerage" in header
                )
        except (IOError, UnicodeDecodeError):
            return False

    def filename(self, filepath: Path) -> str:
        return f"selfwealth.{filepath.name}"

    def account(self, filepath: Path) -> str:
        return self.cash_account

    def extract(self, filepath: Path, existing_entries=None):
        entries = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for index, row in enumerate(reader):
                try:
                    date_str = row.get("Trade Date", row.get("Date", ""))
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                        try:
                            date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue

                    symbol = row.get("Code", row.get("Symbol", "")).strip().upper()
                    trade_type = row.get("Type", "").strip().upper()

                    quantity = D(row.get("Quantity", "0").replace(",", ""))
                    price = D(row.get("Price", "0").replace(",", "").replace("$", ""))

                    brokerage_str = row.get("Brokerage", "0")
                    brokerage = D(brokerage_str.replace(",", "").replace("$", ""))

                    gst_str = row.get("GST", "0")
                    gst = D(gst_str.replace(",", "").replace("$", ""))

                    total_fees = brokerage + gst

                    total_str = row.get("Total", "0")
                    total = D(total_str.replace(",", "").replace("$", ""))

                    meta = data.new_metadata(str(filepath), index)

                    postings = []

                    if trade_type in ["BUY", "B"]:
                        postings.append(
                            data.Posting(
                                f"{self.investment_account_prefix}:{symbol}",
                                amount.Amount(quantity, symbol),
                                data.Cost(price, self.currency, date, None),
                                None,
                                None,
                                None,
                            )
                        )
                        if total_fees > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(total_fees, self.currency),
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                        postings.append(
                            data.Posting(
                                self.cash_account,
                                amount.Amount(-total, self.currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        narration = f"Buy {quantity} {symbol} @ {price}"

                    elif trade_type in ["SELL", "S"]:
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
                        if total_fees > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(total_fees, self.currency),
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                        postings.append(
                            data.Posting(
                                self.cash_account,
                                amount.Amount(total, self.currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        narration = f"Sell {quantity} {symbol} @ {price}"
                    else:
                        continue

                    txn = data.Transaction(
                        meta=meta,
                        date=date,
                        flag="*",
                        payee="SelfWealth",
                        narration=narration,
                        tags=frozenset(),
                        links=frozenset(),
                        postings=postings,
                    )
                    entries.append(txn)
                except (KeyError, ValueError):
                    continue

        return entries
