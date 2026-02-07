#!/usr/bin/env python
"""Load retail data into Fabric SQL Database."""

import struct
import os

import pyodbc
from azure.identity import AzureCliCredential

SERVER = os.environ.get("FABRIC_SQL_SERVER", "<your-fabric-sql-server>.database.fabric.microsoft.com")
DATABASE = os.environ.get("FABRIC_SQL_DATABASE", "<your-fabric-sql-database>")
DRIVER = "{ODBC Driver 18 for SQL Server}"


def get_connection():
    credential = AzureCliCredential()
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    SQL_COPT_SS_ACCESS_TOKEN = 1256
    conn_string = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
    conn = pyodbc.connect(
        conn_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
    )
    return conn


def execute_sql_file(conn, filepath):
    """Execute SQL statements from a file."""
    print(f"Loading SQL from: {filepath}")
    cursor = conn.cursor()

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by GO statements or semicolons for batch execution
    # For large INSERT statements, we need to be careful
    statements = []
    current_stmt = []

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.upper() == "GO":
            if current_stmt:
                statements.append("\n".join(current_stmt))
                current_stmt = []
        else:
            current_stmt.append(line)

    if current_stmt:
        statements.append("\n".join(current_stmt))

    # If no GO statements found, try splitting by semicolons at end of lines
    if len(statements) == 1:
        content = statements[0]
        statements = []
        current_stmt = []

        for line in content.split("\n"):
            current_stmt.append(line)
            stripped = line.strip()
            # Check if line ends with semicolon (end of statement)
            if stripped.endswith(";") and not stripped.startswith("--"):
                stmt = "\n".join(current_stmt).strip()
                if stmt:
                    statements.append(stmt)
                current_stmt = []

        if current_stmt:
            stmt = "\n".join(current_stmt).strip()
            if stmt:
                statements.append(stmt)

    print(f"Found {len(statements)} SQL statements to execute")

    for i, stmt in enumerate(statements):
        stmt = stmt.strip()
        if not stmt or stmt.startswith("--"):
            continue
        try:
            cursor.execute(stmt)
            cursor.commit()
            if i % 10 == 0:
                print(f"Executed statement {i + 1}/{len(statements)}")
        except Exception as e:
            print(f"Error executing statement {i + 1}: {str(e)[:100]}")
            # Continue with next statement
            continue

    print("Done!")
    cursor.close()


def main():
    conn = get_connection()
    print("Connected to Fabric SQL Database!")

    # Execute retail data SQL
    sql_file = "infra/scripts/fabric_scripts/sql_files/retail_data_sql.sql"
    execute_sql_file(conn, sql_file)

    conn.close()


if __name__ == "__main__":
    main()
    main()
