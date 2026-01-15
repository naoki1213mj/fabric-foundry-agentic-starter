# Fabric Data Agent Skill

## 概要

Microsoft Fabric Data Agent を活用した自然言語クエリ。

## 機能

### NL2SQL

```
User: 「今月の売上トップ10は？」
     ↓
SQL: SELECT TOP 10 ProductName, SUM(Sales) 
     FROM dbo.Sales 
     WHERE OrderDate >= DATEADD(month, -1, GETDATE())
     GROUP BY ProductName
     ORDER BY SUM(Sales) DESC
```

### NL2DAX

```
User: 「前年同期比の成長率は？」
     ↓
DAX: CALCULATE(
       DIVIDE(
         [Total Sales] - [Previous Year Sales],
         [Previous Year Sales]
       )
     )
```

## Ontology

ビジネスコンテキストを提供：

```json
{
  "entities": {
    "Customer": {
      "table": "dbo.Customers",
      "columns": ["CustomerId", "CustomerName", "Segment"]
    },
    "Product": {
      "table": "dbo.Products",
      "columns": ["ProductId", "ProductName", "Category"]
    }
  },
  "relationships": [
    {"from": "Sales.CustomerId", "to": "Customers.CustomerId"}
  ]
}
```
