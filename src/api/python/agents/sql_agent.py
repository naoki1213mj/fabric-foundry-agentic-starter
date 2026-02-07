"""
SQL Agent Handler

Handles database queries using Fabric SQL Database.
Provides the run_sql_query tool implementation.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


class SqlAgentHandler:
    """Handler for SQL Agent tool execution."""

    def __init__(self, pyodbc_conn):
        """
        Initialize the SQL Agent Handler.

        Args:
            pyodbc_conn: Active pyodbc connection to Fabric SQL Database
        """
        self.conn = pyodbc_conn

    async def run_sql_query(self, sql_query: str) -> str:
        """
        Execute a SQL query and return results as JSON.

        Args:
            sql_query: Valid T-SQL query to execute

        Returns:
            JSON string containing query results
        """
        try:
            if not self.conn:
                return json.dumps({"error": "Database connection not available"})

            # SQL injection protection: only allow SELECT statements
            sql_stripped = sql_query.strip().upper()
            if not sql_stripped.startswith("SELECT"):
                return json.dumps({"error": "Only SELECT queries are allowed"})

            dangerous_keywords = [
                "INSERT",
                "UPDATE",
                "DELETE",
                "DROP",
                "CREATE",
                "ALTER",
                "EXEC",
                "EXECUTE",
                "TRUNCATE",
                "MERGE",
                "GRANT",
                "REVOKE",
                "INTO",
            ]
            if ";" in sql_query:
                return json.dumps({"error": "Semicolons are not allowed in queries"})
            for kw in dangerous_keywords:
                if re.search(rf"\b{kw}\b", sql_stripped):
                    return json.dumps({"error": f"Dangerous SQL keyword detected: {kw}"})

            cursor = self.conn.cursor()
            cursor.execute(sql_query)

            # Get column names
            columns = [column[0] for column in cursor.description] if cursor.description else []

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    # Handle special types
                    if value is None:
                        row_dict[columns[i]] = None
                    elif isinstance(value, (int, float, str, bool)):
                        row_dict[columns[i]] = value
                    else:
                        row_dict[columns[i]] = str(value)
                results.append(row_dict)

            cursor.close()

            logger.info(f"SQL query executed successfully. Rows returned: {len(results)}")
            return json.dumps(results, ensure_ascii=False, default=str)

        except Exception as e:
            logger.error(f"SQL query execution error: {e}")
            return json.dumps({"error": str(e)})

    def get_tools(self) -> list[callable]:
        """Return the list of tools for the SQL Agent."""
        return [self.run_sql_query]
