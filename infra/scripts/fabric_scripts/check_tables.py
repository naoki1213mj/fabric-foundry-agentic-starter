#!/usr/bin/env python
"""Check tables in Fabric SQL Database."""

import struct

import pyodbc
from azure.identity import AzureCliCredential

SERVER = "l3mc2ebyyfwejehdghpbjlhnw4-moiagz2ftahudlx3khcgjqxfqa.database.fabric.microsoft.com"
DATABASE = "retail_sqldatabase_daj6dri4yf3k3z-c9a4f960-6dfe-4e75-8ef6-ac9ef3f35e44"
DRIVER = "{ODBC Driver 18 for SQL Server}"

credential = AzureCliCredential()
token = credential.get_token("https://database.windows.net/.default")
token_bytes = token.token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

SQL_COPT_SS_ACCESS_TOKEN = 1256
conn_string = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
conn = pyodbc.connect(
    conn_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
)

cursor = conn.cursor()
cursor.execute(
    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
)
tables = cursor.fetchall()
print("=== Tables in Database ===")
for t in tables:
    print(f"  - {t[0]}")

# Count rows in some tables
print("\n=== Row Counts ===")
for table in [t[0] for t in tables]:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = cursor.fetchone()[0]
        print(f"{table}: {count} rows")
    except Exception as e:
        print(f"{table}: Error - {e}")

conn.close()
conn.close()
