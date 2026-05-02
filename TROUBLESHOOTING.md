# Troubleshooting Guide - P007 Revenue Leakage Agent

This document captures solutions to common issues encountered during project development.

---

## Network & Dependency Issues

### PyPI Connection Blocked (Corporate/ISP Firewall)

**Symptoms:**
- `pip install` fails with `ConnectionResetError(10054)`
- Multiple "Retrying" warnings followed by "No matching distribution found"
- Network/corporate firewall blocking `files.pythonhosted.org`

**Solution:**
```bash
pip install <package> --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

**Example:**
```bash
pip install openpyxl --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

**Why it works:** Bypasses SSL certificate checks that corporate proxies sometimes interfere with.

**Applies to:** All pip installations in this project.

---

### openpyxl Installation Failure

**Symptom:**
```
ERROR: No matching distribution found for openpyxl
```

**Solution:**
Use the `--trusted-host` flags:
```bash
pip install openpyxl --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

**Alternative:** Use CSV files instead of Excel (code supports both formats).

---

## File Path Issues

### "No PDF files found" / "Billing file not found"

**Cause:** Running scripts from wrong directory (VS Code debugger changes working directory).

**Symptoms:**
- Script can't find files in `data/` folder
- Error: `FileNotFoundError: Billing file not found: data/sample_billing.csv`

**Solution:** Always run from repo root:
```bash
cd C:\Users\Ulor\Downloads\Claude\Projects\P007\revenue-leakage-agent
python src/tools/script_name.py
```

**Don't use:** VS Code's debugger (F5) - it changes the working directory to parent folder.

**Do use:** PowerShell/Terminal directly from repo root.

---

## Database Issues

### MySQL Command Line Not Found

**Symptom:**
```
mysql : The term 'mysql' is not recognized as the name of a cmdlet...
```

**Cause:** MySQL Server is installed and running, but `mysql.exe` is not in Windows PATH.

**Check if server is running:**
```bash
Get-Service -Name MySQL*
```

**Solutions:**

**Option 1:** Use MySQL Workbench GUI instead of command line.

**Option 2:** Add MySQL to PATH:
1. Find MySQL bin folder (usually `C:\Program Files\MySQL\MySQL Server 8.0\bin\`)
2. Add to Windows PATH environment variable
3. Restart PowerShell

**Option 3:** Use Python scripts to set up databases (recommended for this project):
```bash
python database/setup_mysql.py
python database/setup_postgres.py
```

---

### PostgreSQL Password URL Encoding

**Symptom:**
SQLAlchemy connection fails when password contains special characters (@, !, etc.).

**Solution:**
Use `urllib.parse.quote_plus()` to encode password in connection string:

```python
from urllib.parse import quote_plus

connection_string = f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{database}"
```

**Example:**
```python
# Password: Pescar@00
from urllib.parse import quote_plus
password_encoded = quote_plus("Pescar@00")  # Returns: Pescar%4000
connection_string = f"postgresql+psycopg2://postgres:{password_encoded}@localhost:5432/revenue_leakage_db"
```

---

### SQLAlchemy Warning with pandas

**Symptom:**
```
UserWarning: pandas only supports SQLAlchemy connectable (engine/connection)...
```

**Cause:** Using raw pymysql/psycopg2 connections instead of SQLAlchemy engine.

**Solution:**
Replace raw database connections with SQLAlchemy:

**Before:**
```python
connection = pymysql.connect(host=host, user=user, password=password, database=database)
df = pd.read_sql(query, connection)
```

**After:**
```python
from sqlalchemy import create_engine
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
df = pd.read_sql(query, engine)
engine.dispose()
```

**Install SQLAlchemy:**
```bash
pip install sqlalchemy --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

---

## Python Environment Issues

### Wrong Python Environment Active

**Symptom:**
Packages not found even after installation, or running wrong Python version.

**Check current environment:**
```bash
python --version
pip list
```

**Solution:**
Always activate virtual environment before running scripts:
```bash
cd C:\Users\Ulor\Downloads\Claude\Projects\P007\revenue-leakage-agent
venv\Scripts\activate
```

**Verify activation:** PowerShell prompt should show `(venv)` prefix:
```
(venv) PS C:\Users\Ulor\downloads\claude\projects\p007\revenue-leakage-agent>
```

---

## Testing Checklist

Before running any script, verify:
- ✅ Virtual environment activated (`(venv)` in prompt)
- ✅ Running from repo root directory
- ✅ Required packages installed (`pip list | grep <package>`)
- ✅ Database services running (if using MySQL/PostgreSQL)

---

## Quick Reference

### Project Structure
```
revenue-leakage-agent/
├── data/                    # Input data files
│   ├── sample_contracts/    # Contract PDFs
│   └── sample_billing.csv   # Billing data
├── database/                # Database setup scripts
│   ├── setup_mysql.py
│   ├── setup_postgres.py
│   └── setup_mysql.sql
├── src/
│   └── tools/              # Core reconciliation tools
└── output/                 # Generated outputs
```

### Common Commands
```bash
# Activate environment
venv\Scripts\activate

# Install package (with network fix)
pip install <package> --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Run from repo root
python src/tools/reconciliation_engine.py

# Check database service
Get-Service -Name MySQL*
Get-Service -Name postgresql*
```

---

## Getting Help

If you encounter an issue not covered here:
1. Check the error message carefully
2. Verify you're in the correct directory and environment
3. Add the solution to this document once resolved
4. Commit the update to help future you (and others)
