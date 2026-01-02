# Beancount Importers

Custom beancount importers for Australian and German banks.

## Supported Banks

### Australian Banks
- **CommBank** - Commonwealth Bank CSV exports
- **Up Bank** - Via [aussie-bean-tools](https://github.com/johnmee/aussie-bean-tools) API
- **ubank** - ubank (formerly 86 400) CSV exports

### Australian Investment Platforms
- **Pearler** - Trade history CSV exports
- **SelfWealth** - Trade history CSV exports

### German Banks
- **N26** - Via [beancount-n26](https://github.com/siddhantgoel/beancount-n26)
- **Sparkasse** - Via [beancount-import-sparkasse](https://github.com/laermannjan/beancount-import-sparkasse)
- **Scalable Capital** - CSV exports (custom importer)

### International
- **Wise** - Via [beancount-importers](https://github.com/Evernight/beancount-importers)
- **Revolut** - Via [beancount-importers](https://github.com/Evernight/beancount-importers)

## Usage

### Extract transactions from CSV files

```bash
# Identify which importer handles each file
bean-identify ~/.config/beancount/import_config.py ~/Downloads/*.csv

# Extract transactions
bean-extract ~/.config/beancount/import_config.py ~/Downloads/*.csv >> ledger.beancount
```

### Up Bank API (requires token)

```bash
# Set your Up Bank API token
export UPBANK_TOKEN="up:yeah:..."

# Download recent transactions
upbank --token $UPBANK_TOKEN recent > /tmp/upbank.json

# Extract to beancount format
bean-extract -e ledger.beancount ~/.config/beancount/import_config.py /tmp/upbank.json
```

## Configuration

Edit `~/.config/beancount/import_config.py` to customize account names:

```python
# Australian accounts
COMMBANK_ACCOUNT = "Assets:AU:CommBank:Checking"
UPBANK_ACCOUNT = "Assets:AU:UpBank"
UBANK_ACCOUNT = "Assets:AU:UBank:Savings"

# German accounts
N26_ACCOUNT = "Assets:DE:N26"
SPARKASSE_ACCOUNT = "Assets:DE:Sparkasse:Checking"
```

## Installing Additional Importers

Some importers require additional pip packages:

```bash
# N26
pip install beancount-n26

# Sparkasse
pip install beancount-import-sparkasse

# Wise/Revolut
pip install beancount-importers

# Up Bank
pip install aussie-bean-tools

# Smart importer (ML-based categorization)
pip install smart_importer
```

## CSV Format Notes

### CommBank
Export as CSV from NetBank. Expected columns:
- Date, Amount, Description, Balance

### ubank
Export transaction history. Expected columns:
- Date, Description, Debit, Credit, Balance

### Pearler / SelfWealth
Export trade history. Expected columns:
- Date, Type, Symbol, Quantity, Price, Brokerage, Total

### Scalable Capital
Export from the app (German format with semicolon delimiter):
- Datum, Typ, ISIN, Name, Stück, Kurs, Betrag, Gebühren
