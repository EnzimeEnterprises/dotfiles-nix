"""Beancount importer for Pearler Australia CSV exports."""

import csv
from datetime import datetime
from pathlib import Path

from beangulp import Importer
from beancount.core import amount, data
from beancount.core.number import D


class PearlerImporter(Importer):
    """Importer for Pearler Australia investment platform CSV exports.

    Pearler typically exports trade history with columns like:
    Date,Type,Symbol,Quantity,Price,Brokerage,Total
    """

    def __init__(
        self,
        cash_account: str,
        investment_account_prefix: str = "Assets:Investments:Pearler",
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
                return "pearler" in filepath.name.lower() or (
                    "symbol" in header and "quantity" in header
                )
        except (IOError, UnicodeDecodeError):
            return False

    def filename(self, filepath: Path) -> str:
        return f"pearler.{filepath.name}"

    def account(self, filepath: Path) -> str:
        return self.cash_account

    def extract(self, filepath: Path, existing_entries=None):
        entries = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for index, row in enumerate(reader):
                try:
                    # Parse date
                    date_str = row.get("Date", row.get("Trade Date", ""))
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                        try:
                            date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue

                    symbol = row.get("Symbol", row.get("Code", "")).strip().upper()
                    trade_type = row.get("Type", row.get("Side", "")).strip().upper()

                    quantity_str = row.get("Quantity", row.get("Units", "0"))
                    quantity = D(quantity_str.replace(",", ""))

                    price_str = row.get("Price", row.get("Unit Price", "0"))
                    price = D(price_str.replace(",", "").replace("$", ""))

                    brokerage_str = row.get("Brokerage", row.get("Fees", "0"))
                    brokerage = D(brokerage_str.replace(",", "").replace("$", ""))

                    total_str = row.get("Total", row.get("Amount", "0"))
                    total = D(total_str.replace(",", "").replace("$", ""))

                    meta = data.new_metadata(str(filepath), index)

                    postings = []

                    if trade_type in ["BUY", "PURCHASE"]:
                        # Buying shares
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
                        if brokerage > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(brokerage, self.currency),
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

                    elif trade_type in ["SELL", "SALE"]:
                        # Selling shares
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
                        if brokerage > 0:
                            postings.append(
                                data.Posting(
                                    self.fees_account,
                                    amount.Amount(brokerage, self.currency),
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
                        # Dividend or other
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
                        narration = f"{trade_type} {symbol}"

                    txn = data.Transaction(
                        meta=meta,
                        date=date,
                        flag="*",
                        payee="Pearler",
                        narration=narration,
                        tags=frozenset(),
                        links=frozenset(),
                        postings=postings,
                    )
                    entries.append(txn)
                except (KeyError, ValueError):
                    continue

        return entries
