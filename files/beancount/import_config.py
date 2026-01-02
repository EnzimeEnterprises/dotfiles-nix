#!/usr/bin/env python3
"""Beancount import configuration.

Usage:
    bean-extract import_config.py ~/Downloads/*.csv
    bean-identify import_config.py ~/Downloads/*.csv

This configuration file sets up importers for:
- Australian banks: CommBank, Up Bank, ubank, Pearler, SelfWealth
- German banks: N26, Sparkasse, Scalable Capital
- International: Wise, Revolut
"""

import sys
from pathlib import Path

# Add local importers to path
sys.path.insert(0, str(Path(__file__).parent))

# Custom importers
from importers.commbank import CommBankImporter
from importers.ubank import UBankImporter
from importers.pearler import PearlerImporter
from importers.selfwealth import SelfWealthImporter
from importers.scalable import ScalableCapitalImporter

# Third-party importers (install via pip)
try:
    from beancount_n26 import N26Importer
except ImportError:
    N26Importer = None

try:
    from beancount_import_sparkasse import SparkasseImporter
except ImportError:
    SparkasseImporter = None

# For Up Bank, you can use aussie-bean-tools
try:
    from aussie_bean_tools import upbank
    UpBankImporter = upbank.UpbankImporter
except ImportError:
    UpBankImporter = None

# Smart importer for ML-based categorization (optional)
try:
    from smart_importer import apply_hooks, PredictPostings
    USE_SMART_IMPORTER = True
except ImportError:
    USE_SMART_IMPORTER = False

# =============================================================================
# ACCOUNT CONFIGURATION
# Edit these to match your beancount account structure
# =============================================================================

# Australian accounts
COMMBANK_ACCOUNT = "Assets:AU:CommBank:Checking"
UPBANK_ACCOUNT = "Assets:AU:UpBank"
UBANK_ACCOUNT = "Assets:AU:UBank:Savings"
PEARLER_CASH = "Assets:AU:Pearler:Cash"
SELFWEALTH_CASH = "Assets:AU:SelfWealth:Cash"

# German accounts
N26_ACCOUNT = "Assets:DE:N26"
SPARKASSE_ACCOUNT = "Assets:DE:Sparkasse:Checking"
SCALABLE_CASH = "Assets:DE:Scalable:Cash"

# International accounts
WISE_ACCOUNT = "Assets:Wise"
REVOLUT_ACCOUNT = "Assets:Revolut"

# Expense accounts
BROKERAGE_FEES = "Expenses:Investment:Brokerage"

# =============================================================================
# IMPORTER CONFIGURATION
# =============================================================================

CONFIG = []

# --- Australian Banks ---

# CommBank
CONFIG.append(CommBankImporter(COMMBANK_ACCOUNT, currency="AUD"))

# Up Bank (via aussie-bean-tools API)
if UpBankImporter:
    CONFIG.append(UpBankImporter(UPBANK_ACCOUNT))

# ubank
CONFIG.append(UBankImporter(UBANK_ACCOUNT, currency="AUD"))

# --- Australian Investment Platforms ---

# Pearler
CONFIG.append(
    PearlerImporter(
        cash_account=PEARLER_CASH,
        investment_account_prefix="Assets:AU:Pearler",
        fees_account=BROKERAGE_FEES,
        currency="AUD",
    )
)

# SelfWealth
CONFIG.append(
    SelfWealthImporter(
        cash_account=SELFWEALTH_CASH,
        investment_account_prefix="Assets:AU:SelfWealth",
        fees_account=BROKERAGE_FEES,
        currency="AUD",
    )
)

# --- German Banks ---

# N26
if N26Importer:
    CONFIG.append(
        N26Importer(
            N26_ACCOUNT,
            language="en",
            # Optional: automatic categorization patterns
            # account_patterns={
            #     "Expenses:Food": ["REWE", "EDEKA", "LIDL"],
            #     "Expenses:Transport": ["DB ", "BVG"],
            # }
        )
    )

# Sparkasse
if SparkasseImporter:
    CONFIG.append(SparkasseImporter(SPARKASSE_ACCOUNT))

# Scalable Capital
CONFIG.append(
    ScalableCapitalImporter(
        cash_account=SCALABLE_CASH,
        investment_account_prefix="Assets:DE:Scalable",
        fees_account=BROKERAGE_FEES,
        currency="EUR",
    )
)

# --- International ---

# Wise - using CSV importer
# For API-based import, see tariochbctools documentation
try:
    from beancount_importers.import_wise import WiseImporter
    CONFIG.append(WiseImporter(WISE_ACCOUNT))
except ImportError:
    pass

# Revolut - using CSV importer
try:
    from beancount_importers.import_revolut import RevolutImporter
    CONFIG.append(RevolutImporter(REVOLUT_ACCOUNT))
except ImportError:
    pass

# =============================================================================
# SMART IMPORTER (Optional ML-based categorization)
# =============================================================================

if USE_SMART_IMPORTER:
    # Wrap importers with ML-based posting prediction
    CONFIG = [apply_hooks(importer, [PredictPostings()]) for importer in CONFIG]

# =============================================================================
# EXTRACTION HOOKS
# =============================================================================

def extract(extracted_entries, existing_entries):
    """Post-processing hook for extracted entries."""
    return extracted_entries
