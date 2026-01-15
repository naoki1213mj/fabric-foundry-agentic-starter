#!/usr/bin/env python
"""Add Managed Identity user to Fabric SQL Database."""

import struct

import pyodbc
from azure.identity import AzureCliCredential

SERVER = "l3mc2ebyyfwejehdghpbjlhnw4-moiagz2ftahudlx3khcgjqxfqa.database.fabric.microsoft.com"
DATABASE = "retail_sqldatabase_daj6dri4yf3k3z-c9a4f960-6dfe-4e75-8ef6-ac9ef3f35e44"
DRIVER = "{ODBC Driver 18 for SQL Server}"

# Both Managed Identities to add
MANAGED_IDENTITIES = [
    "api-daj6dri4yf3k3z",  # System Assigned Managed Identity
    "daj6dri4yf3k3z-backend-app-mi",  # User Assigned Managed Identity
]

credential = AzureCliCredential()
token = credential.get_token("https://database.windows.net/.default")
token_bytes = token.token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

SQL_COPT_SS_ACCESS_TOKEN = 1256
conn_string = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
conn = pyodbc.connect(
    conn_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
)
print("Connected!")

cursor = conn.cursor()

for mi_name in MANAGED_IDENTITIES:
    print(f"\nAdding Managed Identity: {mi_name}")

    # Create user from external provider (Managed Identity)
    try:
        cursor.execute(f"CREATE USER [{mi_name}] FROM EXTERNAL PROVIDER;")
        cursor.commit()
        print(f"  Created user {mi_name}")
    except Exception as e:
        print(f"  User creation error (may already exist): {e}")

    # Add to db_datareader role
    try:
        cursor.execute(f"ALTER ROLE db_datareader ADD MEMBER [{mi_name}];")
        cursor.commit()
        print("  Added to db_datareader role")
    except Exception as e:
        print(f"  db_datareader role error: {e}")

    # Add to db_datawriter role
    try:
        cursor.execute(f"ALTER ROLE db_datawriter ADD MEMBER [{mi_name}];")
        cursor.commit()
        print("  Added to db_datawriter role")
    except Exception as e:
        print(f"  db_datawriter role error: {e}")

conn.close()
print("\nDone!")
