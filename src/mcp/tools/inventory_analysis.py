"""
Inventory Analysis Tools

Provides tools for inventory management including turnover rate calculation,
reorder point determination, and slow-moving inventory identification.
"""

import json
from typing import Any


class InventoryAnalysisTools:
    """Inventory analysis and management tools."""

    def get_tool_definitions(self) -> list[dict]:
        """Return MCP tool definitions for inventory analysis tools."""
        return [
            {
                "name": "calculate_inventory_turnover",
                "description": "在庫回転率を計算します。売上原価と平均在庫から回転率と回転日数を算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cost_of_goods_sold": {
                            "type": "number",
                            "description": "売上原価（期間中）",
                        },
                        "average_inventory": {"type": "number", "description": "平均在庫金額"},
                        "period_days": {
                            "type": "integer",
                            "description": "対象期間（日数）",
                            "default": 365,
                        },
                        "product_name": {"type": "string", "description": "製品名（オプション）"},
                    },
                    "required": ["cost_of_goods_sold", "average_inventory"],
                },
            },
            {
                "name": "calculate_reorder_point",
                "description": "発注点（リオーダーポイント）を計算します。需要予測と安全在庫から適正発注タイミングを算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "daily_demand": {"type": "number", "description": "1日あたりの平均需要量"},
                        "lead_time_days": {
                            "type": "integer",
                            "description": "発注から納品までのリードタイム（日数）",
                        },
                        "safety_stock_days": {
                            "type": "integer",
                            "description": "安全在庫日数",
                            "default": 7,
                        },
                        "demand_variability": {
                            "type": "number",
                            "description": "需要の変動係数（標準偏差/平均）",
                            "default": 0.2,
                        },
                    },
                    "required": ["daily_demand", "lead_time_days"],
                },
            },
            {
                "name": "identify_slow_moving_inventory",
                "description": "滞留在庫（デッドストック/スローモービング）を特定します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "inventory_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit_cost": {"type": "number"},
                                    "days_in_stock": {"type": "integer"},
                                    "monthly_sales": {"type": "number"},
                                },
                            },
                            "description": "在庫アイテムリスト",
                        },
                        "slow_moving_threshold_days": {
                            "type": "integer",
                            "description": "滞留判定日数（デフォルト: 90日）",
                            "default": 90,
                        },
                    },
                    "required": ["inventory_items"],
                },
            },
        ]

    def calculate_inventory_turnover(
        self,
        cost_of_goods_sold: float,
        average_inventory: float,
        period_days: int = 365,
        product_name: str | None = None,
    ) -> str:
        """
        Calculate inventory turnover rate.

        Args:
            cost_of_goods_sold: Cost of goods sold for the period
            average_inventory: Average inventory value
            period_days: Period in days (default: 365)
            product_name: Product name (optional)

        Returns:
            JSON string with turnover analysis
        """
        if average_inventory <= 0:
            return json.dumps(
                {
                    "error": "平均在庫は正の値である必要があります",
                    "average_inventory": average_inventory,
                },
                ensure_ascii=False,
            )

        # Inventory turnover ratio
        turnover_ratio = cost_of_goods_sold / average_inventory

        # Days inventory outstanding (DIO)
        days_in_inventory = period_days / turnover_ratio if turnover_ratio > 0 else float("inf")

        # Rating based on turnover
        if turnover_ratio >= 12:  # Monthly turnover or faster
            rating = "★★★★★ 非常に高回転"
            recommendation = "在庫を増やして機会損失を防ぐ検討"
        elif turnover_ratio >= 6:  # Bi-monthly
            rating = "★★★★☆ 高回転"
            recommendation = "良好な在庫管理。現状維持"
        elif turnover_ratio >= 4:  # Quarterly
            rating = "★★★☆☆ 標準"
            recommendation = "適正在庫。季節変動に注意"
        elif turnover_ratio >= 2:  # Semi-annual
            rating = "★★☆☆☆ やや低回転"
            recommendation = "在庫削減を検討。販促強化"
        else:
            rating = "★☆☆☆☆ 低回転"
            recommendation = "滞留在庫の可能性。処分検討"

        result = {
            "product_name": product_name or "対象製品",
            "input_data": {
                "cost_of_goods_sold": cost_of_goods_sold,
                "average_inventory": average_inventory,
                "period_days": period_days,
            },
            "metrics": {
                "turnover_ratio": round(turnover_ratio, 2),
                "days_in_inventory": round(days_in_inventory, 1),
                "turns_per_year": round(turnover_ratio * (365 / period_days), 2),
            },
            "rating": rating,
            "recommendation": recommendation,
            "analysis": f"在庫回転分析: 回転率 {turnover_ratio:.2f}回 / 滞留日数 {days_in_inventory:.0f}日 - {rating}",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_reorder_point(
        self,
        daily_demand: float,
        lead_time_days: int,
        safety_stock_days: int = 7,
        demand_variability: float = 0.2,
    ) -> str:
        """
        Calculate reorder point.

        Args:
            daily_demand: Average daily demand
            lead_time_days: Lead time in days
            safety_stock_days: Safety stock in days
            demand_variability: Demand variability coefficient

        Returns:
            JSON string with reorder point calculation
        """
        # Lead time demand
        lead_time_demand = daily_demand * lead_time_days

        # Safety stock calculation (simple method)
        safety_stock = daily_demand * safety_stock_days

        # Adjusted safety stock with variability
        # Using simplified formula: SS = z * σ * √LT
        # where z ≈ 1.65 for 95% service level
        z_score = 1.65
        std_dev = daily_demand * demand_variability
        statistical_safety_stock = z_score * std_dev * (lead_time_days**0.5)

        # Use the larger of fixed days SS or statistical SS
        final_safety_stock = max(safety_stock, statistical_safety_stock)

        # Reorder point
        reorder_point = lead_time_demand + final_safety_stock

        # Economic order quantity (simplified)
        # Assuming ordering cost = 5000, holding cost = 20% of item value
        annual_demand = daily_demand * 365
        ordering_cost = 5000  # Fixed assumption
        holding_cost_rate = 0.2
        avg_item_cost = 1000  # Placeholder - would need actual cost

        eoq = ((2 * annual_demand * ordering_cost) / (holding_cost_rate * avg_item_cost)) ** 0.5

        result = {
            "input_parameters": {
                "daily_demand": daily_demand,
                "lead_time_days": lead_time_days,
                "safety_stock_days": safety_stock_days,
                "demand_variability": demand_variability,
            },
            "calculations": {
                "lead_time_demand": round(lead_time_demand, 0),
                "safety_stock_fixed": round(safety_stock, 0),
                "safety_stock_statistical": round(statistical_safety_stock, 0),
                "final_safety_stock": round(final_safety_stock, 0),
                "reorder_point": round(reorder_point, 0),
            },
            "recommendations": {
                "reorder_point": round(reorder_point, 0),
                "suggested_order_quantity": round(eoq, 0),
                "max_stock_level": round(reorder_point + eoq, 0),
            },
            "service_level": "95%（z=1.65）",
            "analysis": f"発注点分析: 在庫が {reorder_point:.0f}個 を下回ったら発注（安全在庫 {final_safety_stock:.0f}個 含む）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def identify_slow_moving_inventory(
        self, inventory_items: list[dict[str, Any]], slow_moving_threshold_days: int = 90
    ) -> str:
        """
        Identify slow-moving and dead stock.

        Args:
            inventory_items: List of inventory items with details
            slow_moving_threshold_days: Days threshold for slow-moving (default: 90)

        Returns:
            JSON string with slow-moving inventory analysis
        """
        if not inventory_items:
            return json.dumps({"error": "在庫アイテムリストが空です"}, ensure_ascii=False)

        analyzed_items = []
        dead_stock = []
        slow_moving = []
        healthy = []
        total_value_at_risk = 0

        for item in inventory_items:
            name = item.get("name", "不明")
            quantity = item.get("quantity", 0)
            unit_cost = item.get("unit_cost", 0)
            days_in_stock = item.get("days_in_stock", 0)
            monthly_sales = item.get("monthly_sales", 0)

            inventory_value = quantity * unit_cost

            # Calculate months of stock
            if monthly_sales > 0:
                months_of_stock = quantity / monthly_sales
            else:
                months_of_stock = float("inf") if quantity > 0 else 0

            # Classify
            if days_in_stock > slow_moving_threshold_days * 2 or (
                monthly_sales == 0 and quantity > 0
            ):
                status = "デッドストック"
                color = "red"
                dead_stock.append(name)
                total_value_at_risk += inventory_value
                action = "即時処分検討（セール/廃棄）"
            elif days_in_stock > slow_moving_threshold_days or months_of_stock > 6:
                status = "スローモービング"
                color = "orange"
                slow_moving.append(name)
                total_value_at_risk += inventory_value * 0.5  # 50% risk
                action = "販促強化/価格見直し"
            else:
                status = "正常"
                color = "green"
                healthy.append(name)
                action = "現状維持"

            analyzed_items.append(
                {
                    "name": name,
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "inventory_value": inventory_value,
                    "days_in_stock": days_in_stock,
                    "monthly_sales": monthly_sales,
                    "months_of_stock": round(months_of_stock, 1)
                    if months_of_stock != float("inf")
                    else "∞",
                    "status": status,
                    "color": color,
                    "recommended_action": action,
                }
            )

        # Sort by risk (dead stock first, then slow moving)
        status_order = {"デッドストック": 0, "スローモービング": 1, "正常": 2}
        analyzed_items.sort(key=lambda x: status_order.get(x["status"], 3))

        result = {
            "analyzed_items": analyzed_items,
            "summary": {
                "total_items": len(inventory_items),
                "dead_stock_count": len(dead_stock),
                "slow_moving_count": len(slow_moving),
                "healthy_count": len(healthy),
                "dead_stock_items": dead_stock,
                "slow_moving_items": slow_moving,
            },
            "financial_impact": {
                "total_value_at_risk": round(total_value_at_risk, 0),
                "recommendation": "早期処分で損失最小化"
                if total_value_at_risk > 0
                else "在庫状態良好",
            },
            "threshold_used": slow_moving_threshold_days,
            "analysis": f"滞留在庫分析: デッドストック {len(dead_stock)}件、スローモービング {len(slow_moving)}件 - リスク金額 ¥{total_value_at_risk:,.0f}",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
