#!/usr/bin/env python
"""Add Managed Identity user to Fabric SQL Database."""

import struct
import os

import pyodbc
from azure.identity import AzureCliCredential

SERVER = os.environ.get("FABRIC_SQL_SERVER", "<your-fabric-sql-server>.database.fabric.microsoft.com")
DATABASE = os.environ.get("FABRIC_SQL_DATABASE", "<your-fabric-sql-database>")
DRIVER = "{ODBC Driver 18 for SQL Server}"

# Both Managed Identities to add - update with your actual managed identity names
MANAGED_IDENTITIES = [
    os.environ.get("API_SYSTEM_MI_NAME", "<your-api-app-name>"),  # System Assigned Managed Identity
    os.environ.get("API_USER_MI_NAME", "<your-user-assigned-mi>"),  # User Assigned Managed Identity
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
