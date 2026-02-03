"""
Sales Analysis Tools

Provides tools for sales data analysis including growth rates, moving averages,
ABC analysis, and sales forecasting.
"""

import json
from typing import Any


class SalesAnalysisTools:
    """Sales analysis tools for business intelligence."""

    def get_tool_definitions(self) -> list[dict]:
        """Return MCP tool definitions for sales analysis tools."""
        return [
            {
                "name": "calculate_yoy_growth",
                "description": "前年同期比（YoY）成長率を計算します。今期と前期の売上から成長率と増減額を算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "current_value": {"type": "number", "description": "今期の売上金額"},
                        "previous_value": {
                            "type": "number",
                            "description": "前期（前年同期）の売上金額",
                        },
                    },
                    "required": ["current_value", "previous_value"],
                },
            },
            {
                "name": "calculate_mom_growth",
                "description": "前月比（MoM）成長率を計算します。今月と先月の売上から成長率と増減額を算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "current_value": {"type": "number", "description": "今月の売上金額"},
                        "previous_value": {"type": "number", "description": "先月の売上金額"},
                    },
                    "required": ["current_value", "previous_value"],
                },
            },
            {
                "name": "calculate_moving_average",
                "description": "移動平均を計算します。時系列データから指定期間の移動平均を算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "時系列の数値データ（古い順）",
                        },
                        "period": {
                            "type": "integer",
                            "description": "移動平均の期間（例: 3ヶ月なら3）",
                            "default": 3,
                        },
                    },
                    "required": ["values"],
                },
            },
            {
                "name": "calculate_abc_analysis",
                "description": "ABC分析（パレート分析）を実行します。売上データからA/B/Cランクに分類。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "number"},
                                },
                            },
                            "description": "アイテム名と売上金額のリスト",
                        },
                        "a_threshold": {
                            "type": "number",
                            "description": "Aランクの累積比率閾値（デフォルト: 0.7 = 70%）",
                            "default": 0.7,
                        },
                        "b_threshold": {
                            "type": "number",
                            "description": "Bランクの累積比率閾値（デフォルト: 0.9 = 90%）",
                            "default": 0.9,
                        },
                    },
                    "required": ["items"],
                },
            },
            {
                "name": "calculate_sales_forecast",
                "description": "簡易売上予測を実行します。過去の売上データから線形回帰で次期予測値を算出。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "historical_values": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "過去の売上データ（古い順）",
                        },
                        "periods_ahead": {
                            "type": "integer",
                            "description": "予測する期間数（デフォルト: 1）",
                            "default": 1,
                        },
                    },
                    "required": ["historical_values"],
                },
            },
        ]

    def calculate_yoy_growth(self, current_value: float, previous_value: float) -> str:
        """
        Calculate Year-over-Year growth rate.

        Args:
            current_value: Current period value
            previous_value: Previous period (same period last year) value

        Returns:
            JSON string with growth rate and change amount
        """
        if previous_value == 0:
            if current_value > 0:
                growth_rate = float("inf")
                growth_rate_str = "∞ (前期がゼロ)"
            else:
                growth_rate = 0
                growth_rate_str = "0%"
        else:
            growth_rate = ((current_value - previous_value) / previous_value) * 100
            growth_rate_str = f"{growth_rate:+.2f}%"

        change_amount = current_value - previous_value
        trend = "増加" if change_amount > 0 else ("減少" if change_amount < 0 else "横ばい")

        result = {
            "growth_rate_percent": round(growth_rate, 2) if growth_rate != float("inf") else None,
            "growth_rate_display": growth_rate_str,
            "change_amount": round(change_amount, 2),
            "current_value": current_value,
            "previous_value": previous_value,
            "trend": trend,
            "analysis": f"前年同期比: {growth_rate_str}（{trend}額: ¥{abs(change_amount):,.0f}）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_mom_growth(self, current_value: float, previous_value: float) -> str:
        """
        Calculate Month-over-Month growth rate.

        Args:
            current_value: Current month value
            previous_value: Previous month value

        Returns:
            JSON string with growth rate and change amount
        """
        if previous_value == 0:
            if current_value > 0:
                growth_rate = float("inf")
                growth_rate_str = "∞ (前月がゼロ)"
            else:
                growth_rate = 0
                growth_rate_str = "0%"
        else:
            growth_rate = ((current_value - previous_value) / previous_value) * 100
            growth_rate_str = f"{growth_rate:+.2f}%"

        change_amount = current_value - previous_value
        trend = "増加" if change_amount > 0 else ("減少" if change_amount < 0 else "横ばい")

        result = {
            "growth_rate_percent": round(growth_rate, 2) if growth_rate != float("inf") else None,
            "growth_rate_display": growth_rate_str,
            "change_amount": round(change_amount, 2),
            "current_value": current_value,
            "previous_value": previous_value,
            "trend": trend,
            "analysis": f"前月比: {growth_rate_str}（{trend}額: ¥{abs(change_amount):,.0f}）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_moving_average(self, values: list[float], period: int = 3) -> str:
        """
        Calculate moving average.

        Args:
            values: Time series data (oldest first)
            period: Moving average period (default: 3)

        Returns:
            JSON string with moving average values
        """
        if len(values) < period:
            return json.dumps(
                {
                    "error": f"データ数({len(values)})が期間({period})より少ないです",
                    "values": values,
                    "period": period,
                },
                ensure_ascii=False,
            )

        moving_averages = []
        for i in range(len(values) - period + 1):
            window = values[i : i + period]
            avg = sum(window) / period
            moving_averages.append(round(avg, 2))

        latest_ma = moving_averages[-1] if moving_averages else None
        trend = None
        if len(moving_averages) >= 2:
            diff = moving_averages[-1] - moving_averages[-2]
            trend = "上昇傾向" if diff > 0 else ("下降傾向" if diff < 0 else "横ばい")

        result = {
            "moving_averages": moving_averages,
            "period": period,
            "latest_value": latest_ma,
            "trend": trend,
            "original_values": values,
            "analysis": f"{period}期間移動平均: 最新値 ¥{latest_ma:,.0f}（{trend}）"
            if latest_ma
            else "計算不可",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_abc_analysis(
        self, items: list[dict[str, Any]], a_threshold: float = 0.7, b_threshold: float = 0.9
    ) -> str:
        """
        Perform ABC (Pareto) analysis.

        Args:
            items: List of {"name": str, "value": number}
            a_threshold: Cumulative ratio threshold for A rank (default: 0.7)
            b_threshold: Cumulative ratio threshold for B rank (default: 0.9)

        Returns:
            JSON string with ABC classification
        """
        if not items:
            return json.dumps({"error": "アイテムリストが空です"}, ensure_ascii=False)

        # Sort by value descending
        sorted_items = sorted(items, key=lambda x: x.get("value", 0), reverse=True)

        total_value = sum(item.get("value", 0) for item in sorted_items)
        if total_value == 0:
            return json.dumps({"error": "合計値がゼロです"}, ensure_ascii=False)

        # Calculate cumulative ratio and assign ranks
        cumulative = 0
        classified_items = []
        a_items, b_items, c_items = [], [], []

        for item in sorted_items:
            value = item.get("value", 0)
            cumulative += value
            cumulative_ratio = cumulative / total_value

            if cumulative_ratio <= a_threshold:
                rank = "A"
                a_items.append(item["name"])
            elif cumulative_ratio <= b_threshold:
                rank = "B"
                b_items.append(item["name"])
            else:
                rank = "C"
                c_items.append(item["name"])

            classified_items.append(
                {
                    "name": item.get("name"),
                    "value": value,
                    "ratio": round(value / total_value * 100, 2),
                    "cumulative_ratio": round(cumulative_ratio * 100, 2),
                    "rank": rank,
                }
            )

        result = {
            "classified_items": classified_items,
            "summary": {
                "A_count": len(a_items),
                "B_count": len(b_items),
                "C_count": len(c_items),
                "A_items": a_items,
                "B_items": b_items,
                "C_items": c_items,
            },
            "thresholds": {"A": a_threshold, "B": b_threshold},
            "total_value": total_value,
            "analysis": f"ABC分析結果: Aランク {len(a_items)}件（売上の{a_threshold * 100:.0f}%を占める重点商品）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_sales_forecast(
        self, historical_values: list[float], periods_ahead: int = 1
    ) -> str:
        """
        Calculate simple linear regression forecast.

        Args:
            historical_values: Historical sales data (oldest first)
            periods_ahead: Number of periods to forecast (default: 1)

        Returns:
            JSON string with forecast values
        """
        n = len(historical_values)
        if n < 2:
            return json.dumps(
                {"error": "予測には最低2期間のデータが必要です", "data_points": n},
                ensure_ascii=False,
            )

        # Simple linear regression: y = a + b*x
        x_values = list(range(1, n + 1))
        y_values = historical_values

        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        # Calculate slope (b) and intercept (a)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        # Forecast future values
        forecasts = []
        for i in range(1, periods_ahead + 1):
            future_x = n + i
            forecast_value = intercept + slope * future_x
            forecasts.append({"period": f"+{i}期", "forecast_value": round(forecast_value, 2)})

        # Calculate trend
        trend = "上昇" if slope > 0 else ("下降" if slope < 0 else "横ばい")
        monthly_change = abs(slope)

        result = {
            "forecasts": forecasts,
            "model": {
                "intercept": round(intercept, 2),
                "slope": round(slope, 2),
                "trend": trend,
                "monthly_change": round(monthly_change, 2),
            },
            "historical_data": {
                "count": n,
                "latest_value": historical_values[-1],
                "average": round(y_mean, 2),
            },
            "analysis": f"売上予測: 次期予測 ¥{forecasts[0]['forecast_value']:,.0f}（{trend}傾向、1期あたり ¥{monthly_change:,.0f}の変動）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
