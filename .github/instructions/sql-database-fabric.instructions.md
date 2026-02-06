---
applyTo: "**/*fabric*.{py,cs,sql},**/*database*.{py,cs}"
---

# SQL Database in Fabric Guidelines

## 接続パターン

```python
import pyodbc
from azure.identity import DefaultAzureCredential

def get_fabric_connection():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.fabric.microsoft.com/.default")

    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={FABRIC_ENDPOINT};"
        f"Database={DATABASE_NAME};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )

    conn = pyodbc.connect(conn_str, attrs_before={
        1256: token.token.encode()  # SQL_COPT_SS_ACCESS_TOKEN
    })
    return conn
```

## クエリ実行

```python
async def execute_query(sql: str, params: tuple = None) -> list:
    """SQLクエリを実行してJSON形式で結果を返す"""
    conn = get_fabric_connection()
    cursor = conn.cursor()

    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)

    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return results
```

## サンプルクエリ（Sales Analyst シナリオ）

> **実際のテーブル**: customer, product, productcategory, orders, orderline, orderpayment, location, customerrelationshiptype, invoice, payment
> **履歴テーブル**: hst_conversations, hst_conversation_messages

```sql
-- トップ製品
SELECT TOP 10
    p.ProductName,
    SUM(ol.LineTotal) as TotalSales,
    COUNT(*) as OrderCount
FROM orders o
JOIN orderline ol ON o.OrderId = ol.OrderId
JOIN product p ON ol.ProductId = p.ProductID
WHERE o.OrderStatus = 'Completed'
GROUP BY p.ProductName
ORDER BY TotalSales DESC;

-- 顧客セグメント分析
SELECT
    crt.CustomerRelationshipTypeName as Segment,
    AVG(o.OrderTotal) as AvgOrderValue,
    COUNT(DISTINCT c.CustomerId) as CustomerCount
FROM orders o
JOIN customer c ON o.CustomerId = c.CustomerId
JOIN customerrelationshiptype crt ON c.CustomerRelationshipTypeId = crt.CustomerRelationshipTypeId
WHERE o.OrderStatus = 'Completed'
GROUP BY crt.CustomerRelationshipTypeName;

-- YoY成長率
SELECT
    YEAR(o.OrderDate) as Year,
    SUM(ol.LineTotal) as Revenue,
    LAG(SUM(ol.LineTotal)) OVER (ORDER BY YEAR(o.OrderDate)) as PrevYearRevenue
FROM orders o
JOIN orderline ol ON o.OrderId = ol.OrderId
WHERE o.OrderStatus = 'Completed'
GROUP BY YEAR(o.OrderDate);
## DEMO_MODE対応

```python
DEMO_DATA = {
    "top_products": [
        {"ProductName": "Product A", "TotalSales": 1500000},
        {"ProductName": "Product B", "TotalSales": 1200000},
    ]
}

async def get_top_products():
    if DEMO_MODE:
        return DEMO_DATA["top_products"]
    return await execute_query("SELECT TOP 10 ...")
```
