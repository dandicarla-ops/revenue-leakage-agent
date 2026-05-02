"""
Billing reconciliation engine - compare contracts vs actual billing.
Supports CSV, Excel, MySQL, and PostgreSQL with auto-detection.
Usage: from src.tools.reconciliation_engine import reconcile_merchant
"""

import pandas as pd
import os
from pathlib import Path

# Database drivers (optional imports)
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

class BillingFormatError(Exception):
    """Raised when billing file format is not supported."""
    pass

def detect_file_format(file_path):
    """
    Auto-detect file format based on file extension.
    
    Args:
        file_path (str): Path to billing file
    
    Returns:
        str: Format type ('csv', 'excel', or raises error)
    """
    ext = Path(file_path).suffix.lower()
    
    if ext == '.csv':
        return 'csv'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    else:
        raise BillingFormatError(f"Unsupported file format: {ext}. Use .csv or .xlsx")

def load_billing_data_from_mysql(host, database, user, password, port=3306, table='billing'):
    """
    Load billing data from MySQL database.
    
    Args:
        host (str): MySQL host
        database (str): Database name
        user (str): MySQL user
        password (str): MySQL password
        port (int): MySQL port (default 3306)
        table (str): Table name (default 'billing')
    
    Returns:
        pd.DataFrame: Billing data
    """
    if not MYSQL_AVAILABLE:
        raise ImportError("pymysql not installed. Run: pip install pymysql")

    try:
        from sqlalchemy import create_engine
        from urllib.parse import quote_plus

        connection_string = f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        engine = create_engine(connection_string)

        query = f"SELECT merchant_id, month, billing_amount, merchant_name FROM {table}"
        df = pd.read_sql(query, engine)
        engine.dispose()
        
        print(f"  ✅ Loaded MySQL: {len(df)} rows from {database}.{table}")
        return df
    
    except Exception as e:
        print(f"  ❌ MySQL error: {e}")
        raise

def load_billing_data_from_postgres(host, database, user, password, port=5432, table='billing'):
    """
    Load billing data from PostgreSQL database.
    
    Args:
        host (str): PostgreSQL host
        database (str): Database name
        user (str): PostgreSQL user
        password (str): PostgreSQL password
        port (int): PostgreSQL port (default 5432)
        table (str): Table name (default 'billing')
    
    Returns:
        pd.DataFrame: Billing data
    """
    if not POSTGRES_AVAILABLE:
        raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")

    try:
        from sqlalchemy import create_engine
        from urllib.parse import quote_plus

        connection_string = f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{database}"
        engine = create_engine(connection_string)

        query = f"SELECT merchant_id, month, billing_amount, merchant_name FROM {table}"
        df = pd.read_sql(query, engine)
        engine.dispose()
        
        print(f"  ✅ Loaded PostgreSQL: {len(df)} rows from {database}.{table}")
        return df
    
    except Exception as e:
        print(f"  ❌ PostgreSQL error: {e}")
        raise

def load_billing_data(source, format_type=None, **db_params):
    """
    Load billing data from CSV, Excel, MySQL, or PostgreSQL.
    
    Args:
        source (str or dict): File path OR database config dict
        format_type (str): 'csv', 'excel', 'mysql', 'postgres', or None for auto-detect
        **db_params: Database connection parameters (if source is db type)
    
    Returns:
        pd.DataFrame: Billing data with columns: merchant_id, month, billing_amount
    
    Examples:
        # File-based
        df = load_billing_data("data/billing.csv")
        df = load_billing_data("data/billing.xlsx")
        
        # Database-based
        df = load_billing_data("mysql", host="localhost", database="revenue_db", 
                               user="root", password="pass")
        df = load_billing_data("postgres", host="localhost", database="revenue_db",
                               user="postgres", password="pass")
    """
    
    # Handle database sources
    if isinstance(source, str) and source.lower() in ['mysql', 'postgres', 'postgresql']:
        format_type = 'mysql' if source.lower() == 'mysql' else 'postgres'
    
    # Database source
    if format_type in ['mysql', 'postgres', 'postgresql']:
        if format_type == 'mysql':
            df = load_billing_data_from_mysql(**db_params)
        else:
            df = load_billing_data_from_postgres(**db_params)
    
    # File source
    else:
        if not os.path.exists(source):
            raise FileNotFoundError(f"Billing file not found: {source}")
        
        # Auto-detect format if not specified
        if format_type is None:
            format_type = detect_file_format(source)
            print(f"  ℹ️  Auto-detected format: {format_type.upper()}")
        
        if format_type.lower() == 'csv':
            df = pd.read_csv(source)
            print(f"  ✅ Loaded CSV: {len(df)} rows")
        
        elif format_type.lower() == 'excel':
            # Inspect available sheets before loading
            xl = pd.ExcelFile(source)
            available_sheets = xl.sheet_names
            print(f"  ℹ️  Available sheets: {available_sheets}")

            required_cols = {'merchant_id', 'month', 'billing_amount'}
            target_sheet = available_sheets[0]
            header_row = 0

            for sheet in available_sheets:
                raw = pd.read_excel(source, sheet_name=sheet, nrows=10, header=None)
                found = False
                for row_idx in range(len(raw)):
                    row_vals = {
                        str(v).strip().lower()
                        for v in raw.iloc[row_idx, :10]
                        if pd.notna(v)
                    }
                    if required_cols.issubset(row_vals):
                        target_sheet = sheet
                        header_row = row_idx
                        found = True
                        print(f"  ℹ️  Found billing columns on row {row_idx + 1} of sheet '{sheet}'")
                        break
                if found:
                    break

            print(f"  ℹ️  Reading sheet: '{target_sheet}' (header row index: {header_row})")
            df = pd.read_excel(source, sheet_name=target_sheet, header=header_row)
            df.columns = [str(c).strip().lower() if pd.notna(c) else c for c in df.columns]
            df.dropna(how='all', inplace=True)
            df.reset_index(drop=True, inplace=True)
            print(f"  ✅ Loaded Excel: {len(df)} rows from sheet '{target_sheet}'")
        
        else:
            raise BillingFormatError(f"Unknown format: {format_type}")
    
    # Validate required columns
    required_cols = ['merchant_id', 'month', 'billing_amount']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Ensure data types
    df['billing_amount'] = pd.to_numeric(df['billing_amount'], errors='coerce')
    df['merchant_id'] = df['merchant_id'].astype(str)
    
    return df

class Discrepancy:
    """Represents a revenue discrepancy for a merchant."""
    
    def __init__(self, merchant_id, merchant_name, month, expected, actual, percentage_shortfall=0):
        self.merchant_id = merchant_id
        self.merchant_name = merchant_name
        self.month = month
        self.expected = expected
        self.actual = actual
        self.shortfall = expected - actual
        self.percentage_shortfall = percentage_shortfall
        
        # Determine severity
        if self.shortfall < 0:
            self.severity = "OVERBILLED"
        elif self.percentage_shortfall == 0:
            self.severity = "MATCH"
        elif self.percentage_shortfall < 5:
            self.severity = "LOW"
        elif self.percentage_shortfall < 15:
            self.severity = "MEDIUM"
        else:
            self.severity = "HIGH"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'merchant_id': self.merchant_id,
            'merchant_name': self.merchant_name,
            'month': self.month,
            'expected': round(self.expected, 2),
            'actual': round(self.actual, 2),
            'shortfall': round(self.shortfall, 2),
            'percentage_shortfall': round(self.percentage_shortfall, 2),
            'severity': self.severity
        }

def reconcile_merchant(merchant_id, merchant_name, min_commitment, billing_df):
    """
    Reconcile a single merchant: compare expected vs actual billing.
    
    Args:
        merchant_id (str): Merchant ID
        merchant_name (str): Merchant name
        min_commitment (float): Monthly minimum commitment
        billing_df (pd.DataFrame): Full billing dataframe
    
    Returns:
        list: List of Discrepancy objects
    """
    
    discrepancies = []
    
    # Filter billing for this merchant
    merchant_billing = billing_df[billing_df['merchant_id'] == merchant_id]
    
    if merchant_billing.empty:
        print(f"  ⚠️  No billing data for {merchant_id}")
        return discrepancies
    
    # Check each month
    for _, row in merchant_billing.iterrows():
        month = row['month']
        actual = row['billing_amount']
        expected = min_commitment
        
        # Calculate percentage shortfall
        if expected > 0:
            pct_shortfall = max(0, ((expected - actual) / expected) * 100)
        else:
            pct_shortfall = 0
        
        # Create discrepancy record
        disc = Discrepancy(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            month=month,
            expected=expected,
            actual=actual,
            percentage_shortfall=pct_shortfall
        )
        
        discrepancies.append(disc)
    
    return discrepancies

def filter_material_discrepancies(discrepancies, threshold_percentage=10.0):
    """
    Filter discrepancies to only material ones (above threshold).
    
    Args:
        discrepancies (list): List of Discrepancy objects
        threshold_percentage (float): Minimum % shortfall to flag
    
    Returns:
        list: Filtered list of significant discrepancies
    """
    material = [
        d for d in discrepancies
        if d.percentage_shortfall >= threshold_percentage and d.shortfall > 0
    ]
    return material

if __name__ == "__main__":
    print("=" * 60)
    print("BILLING RECONCILIATION ENGINE TEST")
    print("=" * 60 + "\n")
    
    # Test data source - change this to test different sources
    # billing_file = "data/sample_billing.csv"

    # Test with MySQL
    # billing_source = "mysql"
    # db_config = {
    #     "host": "localhost",
    #     "database": "revenue_leakage_db",
    #     "user": "root",
    #     "password": "Pescar@00",
    #     "table": "billing"
    # }

    # Test with PostgreSQL
    billing_source = "postgres"
    db_config = {
        "host": "localhost",
        "database": "revenue_leakage_db",
        "user": "postgres",
        "password": "Pescar@00",
        "table": "billing"
    }
    
    try:
        # Load billing data
        print("Loading billing data...")
        
        # For database sources
        billing_df = load_billing_data(billing_source, **db_config)

        # For file sources
        # billing_df = load_billing_data(billing_file)
        
        # Example merchant
        merchant_id = "M001"
        merchant_name = "TechFlow Inc."
        min_commitment = 50000
        
        print(f"\nReconciling: {merchant_name} ({merchant_id})")
        print(f"Monthly Minimum Commitment: ${min_commitment:,.0f}\n")
        
        # Reconcile
        discrepancies = reconcile_merchant(merchant_id, merchant_name, min_commitment, billing_df)
        
        # Filter material discrepancies
        material = filter_material_discrepancies(discrepancies, threshold_percentage=10.0)
        
        print(f"Total months: {len(discrepancies)}")
        print(f"Material discrepancies (>10%): {len(material)}\n")
        
        if material:
            print("Material shortfalls:")
            for d in material:
                print(f"  {d.month}: Expected ${d.expected:,.0f}, Actual ${d.actual:,.0f}, Shortfall ${d.shortfall:,.0f} ({d.percentage_shortfall:.1f}%)")
        else:
            print("No material discrepancies found.")
    
    except Exception as e:
        print(f"❌ Error: {e}")