"""
MCP Client for Business Analytics Tools

Connects to the Azure Functions MCP server to provide business analytics tools
to the chat agent. Tools include sales analysis, product comparison,
customer segmentation, and inventory analysis.
"""

import json
import logging
import os
from typing import Annotated

import httpx
from agent_framework import tool

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:7071/api/mcp")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"

# Cache for MCP tools (loaded once at startup)
_mcp_tool_definitions: list[dict] | None = None

# Shared httpx client for MCP server communication (reuses TCP connections)
_httpx_client: httpx.AsyncClient | None = None


def _get_httpx_client() -> httpx.AsyncClient:
    """Get or create the shared httpx.AsyncClient."""
    global _httpx_client
    if _httpx_client is None or _httpx_client.is_closed:
        _httpx_client = httpx.AsyncClient(timeout=30.0)
    return _httpx_client


async def close_httpx_client() -> None:
    """Close the shared httpx client. Call during application shutdown."""
    global _httpx_client
    if _httpx_client is not None and not _httpx_client.is_closed:
        await _httpx_client.aclose()
        _httpx_client = None


# MCP tool name to display label mapping for tool events
MCP_TOOL_LABELS = {
    "calculate_yoy_growth": "前年比成長率を計算中",
    "calculate_mom_growth": "前月比成長率を計算中",
    "calculate_moving_average": "移動平均を計算中",
    "calculate_abc_analysis": "ABC分析を実行中",
    "calculate_sales_forecast": "売上予測を実行中",
    "calculate_rfm_score": "RFMスコアを計算中",
    "classify_customer_segment": "顧客セグメントを分類中",
    "calculate_clv": "顧客生涯価値を計算中",
    "recommend_next_action": "次のアクションを推奨中",
    "calculate_inventory_turnover": "在庫回転率を計算中",
    "calculate_reorder_point": "再発注点を計算中",
    "identify_slow_moving_inventory": "滞留在庫を特定中",
    "compare_products": "製品比較を実行中",
    "calculate_price_performance": "価格性能比を計算中",
    "calculate_bundle_discount": "バンドル割引を計算中",
}


async def fetch_mcp_tools() -> list[dict]:
    """Fetch tool definitions from the MCP server."""
    global _mcp_tool_definitions
    if _mcp_tool_definitions is not None:
        return _mcp_tool_definitions

    try:
        client = _get_httpx_client()
        response = await client.post(
            MCP_SERVER_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()
        if "result" in result and "tools" in result["result"]:
            _mcp_tool_definitions = result["result"]["tools"]
            logger.info(f"Loaded {len(_mcp_tool_definitions)} tools from MCP server")
            return _mcp_tool_definitions
        else:
            logger.warning(f"Unexpected MCP response: {result}")
            return []
    except Exception as e:
        logger.warning(f"Failed to fetch MCP tools: {e}")
        return []


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on the MCP server.

    Args:
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool

    Returns:
        JSON string with tool result or error
    """
    # Import emit_tool_event from chat module (avoid circular import)
    try:
        from chat import emit_tool_event
    except ImportError:
        emit_tool_event = None

    # Emit tool start event
    tool_label = MCP_TOOL_LABELS.get(tool_name, tool_name)
    if emit_tool_event:
        await emit_tool_event(tool_name, "started", f"{tool_label}...")

    try:
        client = _get_httpx_client()
        response = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        )
        response.raise_for_status()
        result = response.json()

        # Emit completion event
        if emit_tool_event:
            await emit_tool_event(tool_name, "completed", "完了")

        if "result" in result:
            content = result["result"].get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", json.dumps(result["result"]))
            return json.dumps(result["result"])
        elif "error" in result:
            return json.dumps({"error": result["error"]}, ensure_ascii=False)
        else:
            return json.dumps(result, ensure_ascii=False)
    except httpx.TimeoutException:
        if emit_tool_event:
            await emit_tool_event(tool_name, "error", "タイムアウト")
        return json.dumps({"error": "MCP server timeout"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        if emit_tool_event:
            await emit_tool_event(tool_name, "error", str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================================
# Sales Analysis Tools - Wrapped as @tool for agent_framework
# ============================================================================


@tool(approval_mode="never_require")
async def calculate_yoy_growth(
    current_value: Annotated[float, "今期の売上金額"],
    previous_value: Annotated[float, "前期（前年同期）の売上金額"],
) -> str:
    """前年同期比（YoY）成長率を計算します。

    今期と前期の売上から成長率と増減額を算出。
    SQLで取得した売上データを元に、成長トレンドを分析する際に使用してください。

    Returns:
        成長率、増減額、トレンド（増加/減少/横ばい）を含むJSON
    """
    return await call_mcp_tool(
        "calculate_yoy_growth", {"current_value": current_value, "previous_value": previous_value}
    )


@tool(approval_mode="never_require")
async def calculate_mom_growth(
    current_value: Annotated[float, "今月の売上金額"],
    previous_value: Annotated[float, "先月の売上金額"],
) -> str:
    """前月比（MoM）成長率を計算します。

    今月と先月の売上から成長率と増減額を算出。
    短期的な売上トレンドを分析する際に使用してください。

    Returns:
        成長率、増減額、トレンドを含むJSON
    """
    return await call_mcp_tool(
        "calculate_mom_growth", {"current_value": current_value, "previous_value": previous_value}
    )


@tool(approval_mode="never_require")
async def calculate_moving_average(
    values: Annotated[list[float], "時系列の数値データ（古い順）"],
    period: Annotated[int, "移動平均の期間（デフォルト: 3）"] = 3,
) -> str:
    """移動平均を計算します。

    時系列データから指定期間の移動平均を算出。
    売上トレンドの平滑化や季節変動の除去に使用してください。

    Returns:
        移動平均値のリスト、最新値、トレンドを含むJSON
    """
    return await call_mcp_tool("calculate_moving_average", {"values": values, "period": period})


@tool(approval_mode="never_require")
async def calculate_abc_analysis(
    items: Annotated[
        list[dict], "アイテム名と売上金額のリスト [{'name': str, 'value': float}, ...]"
    ],
    a_threshold: Annotated[float, "Aランクの累積比率閾値（デフォルト: 0.7）"] = 0.7,
    b_threshold: Annotated[float, "Bランクの累積比率閾値（デフォルト: 0.9）"] = 0.9,
) -> str:
    """ABC分析（パレート分析）を実行します。

    売上データからA/B/Cランクに分類。
    重点商品の特定や在庫管理の優先順位付けに使用してください。

    Returns:
        各アイテムのランク、サマリー、分析結果を含むJSON
    """
    return await call_mcp_tool(
        "calculate_abc_analysis",
        {"items": items, "a_threshold": a_threshold, "b_threshold": b_threshold},
    )


@tool(approval_mode="never_require")
async def calculate_sales_forecast(
    historical_values: Annotated[list[float], "過去の売上データ（古い順）"],
    periods_ahead: Annotated[int, "予測する期間数（デフォルト: 1）"] = 1,
) -> str:
    """簡易売上予測を実行します。

    過去の売上データから線形回帰で次期予測値を算出。
    売上計画の策定や目標設定に使用してください。

    Returns:
        予測値、モデル情報、分析結果を含むJSON
    """
    return await call_mcp_tool(
        "calculate_sales_forecast",
        {"historical_values": historical_values, "periods_ahead": periods_ahead},
    )


# ============================================================================
# Customer Segmentation Tools
# ============================================================================


@tool(approval_mode="never_require")
async def calculate_rfm_score(
    recency_days: Annotated[int, "最終購入からの日数"],
    frequency: Annotated[int, "購入回数（期間内）"],
    monetary: Annotated[float, "累計購入金額"],
    customer_id: Annotated[str | None, "顧客ID（オプション）"] = None,
) -> str:
    """RFM分析（Recency, Frequency, Monetary）スコアを計算します。

    顧客の購買行動を3軸で評価。
    顧客セグメンテーションやターゲティングに使用してください。

    Returns:
        R/F/Mスコア、合計スコア、分析結果を含むJSON
    """
    args = {"recency_days": recency_days, "frequency": frequency, "monetary": monetary}
    if customer_id:
        args["customer_id"] = customer_id
    return await call_mcp_tool("calculate_rfm_score", args)


@tool(approval_mode="never_require")
async def classify_customer_segment(
    r_score: Annotated[int, "Recencyスコア（1-5）"],
    f_score: Annotated[int, "Frequencyスコア（1-5）"],
    m_score: Annotated[int, "Monetaryスコア（1-5）"],
    customer_id: Annotated[str | None, "顧客ID（オプション）"] = None,
) -> str:
    """RFMスコアに基づいて顧客をセグメント分類します。

    VIP顧客、優良顧客、休眠顧客などに分類。
    マーケティング施策の対象選定に使用してください。

    Returns:
        セグメント名、説明、推奨アクションを含むJSON
    """
    args = {"r_score": r_score, "f_score": f_score, "m_score": m_score}
    if customer_id:
        args["customer_id"] = customer_id
    return await call_mcp_tool("classify_customer_segment", args)


@tool(approval_mode="never_require")
async def calculate_clv(
    average_purchase_value: Annotated[float, "平均購入単価"],
    purchase_frequency_per_year: Annotated[float, "年間平均購入回数"],
    customer_lifespan_years: Annotated[float, "顧客継続年数（予測）"] = 3,
    profit_margin: Annotated[float, "利益率（0-1）"] = 0.3,
    discount_rate: Annotated[float, "割引率（NPV計算用）"] = 0.1,
) -> str:
    """顧客生涯価値（CLV: Customer Lifetime Value）を計算します。

    顧客の長期的な価値を金額で算出。
    顧客獲得コストの上限設定や投資判断に使用してください。

    Returns:
        CLV金額、年間収益、ティア分類を含むJSON
    """
    return await call_mcp_tool(
        "calculate_clv",
        {
            "average_purchase_value": average_purchase_value,
            "purchase_frequency_per_year": purchase_frequency_per_year,
            "customer_lifespan_years": customer_lifespan_years,
            "profit_margin": profit_margin,
            "discount_rate": discount_rate,
        },
    )


@tool(approval_mode="never_require")
async def recommend_next_action(
    segment: Annotated[str, "顧客セグメント名"],
    rfm_scores: Annotated[dict | None, "RFMスコア {r: int, f: int, m: int}"] = None,
    last_purchase_days: Annotated[int | None, "最終購入からの日数"] = None,
) -> str:
    """顧客セグメントに基づいてNext Best Actionを提案します。

    各セグメントに最適なマーケティングアクションを推奨。
    キャンペーン企画やCRM施策に使用してください。

    Returns:
        推奨アクション、チャネル、優先度を含むJSON
    """
    args = {"segment": segment}
    if rfm_scores:
        args["rfm_scores"] = rfm_scores
    if last_purchase_days is not None:
        args["last_purchase_days"] = last_purchase_days
    return await call_mcp_tool("recommend_next_action", args)


# ============================================================================
# Inventory Analysis Tools
# ============================================================================


@tool(approval_mode="never_require")
async def calculate_inventory_turnover(
    cost_of_goods_sold: Annotated[float, "売上原価（期間中）"],
    average_inventory: Annotated[float, "平均在庫金額"],
    period_days: Annotated[int, "対象期間（日数）"] = 365,
    product_name: Annotated[str | None, "製品名（オプション）"] = None,
) -> str:
    """在庫回転率を計算します。

    売上原価と平均在庫から回転率と回転日数を算出。
    在庫効率の評価や改善に使用してください。

    Returns:
        回転率、回転日数、評価を含むJSON
    """
    args = {
        "cost_of_goods_sold": cost_of_goods_sold,
        "average_inventory": average_inventory,
        "period_days": period_days,
    }
    if product_name:
        args["product_name"] = product_name
    return await call_mcp_tool("calculate_inventory_turnover", args)


@tool(approval_mode="never_require")
async def calculate_reorder_point(
    daily_demand: Annotated[float, "1日あたりの平均需要量"],
    lead_time_days: Annotated[int, "発注から納品までのリードタイム（日数）"],
    safety_stock_days: Annotated[int, "安全在庫日数"] = 7,
    demand_variability: Annotated[float, "需要の変動係数"] = 0.2,
) -> str:
    """発注点（リオーダーポイント）を計算します。

    需要予測と安全在庫から適正発注タイミングを算出。
    在庫切れ防止と過剰在庫回避に使用してください。

    Returns:
        発注点、安全在庫、推奨発注量を含むJSON
    """
    return await call_mcp_tool(
        "calculate_reorder_point",
        {
            "daily_demand": daily_demand,
            "lead_time_days": lead_time_days,
            "safety_stock_days": safety_stock_days,
            "demand_variability": demand_variability,
        },
    )


@tool(approval_mode="never_require")
async def identify_slow_moving_inventory(
    inventory_items: Annotated[
        list[dict],
        "在庫アイテムリスト [{'name': str, 'quantity': float, 'unit_cost': float, 'days_in_stock': int, 'monthly_sales': float}, ...]",
    ],
    slow_moving_threshold_days: Annotated[int, "滞留判定日数（デフォルト: 90日）"] = 90,
) -> str:
    """滞留在庫（デッドストック/スローモービング）を特定します。

    在庫データからリスクのある在庫を分類。
    在庫処分やプロモーション計画に使用してください。

    Returns:
        分類結果、リスク金額、推奨アクションを含むJSON
    """
    return await call_mcp_tool(
        "identify_slow_moving_inventory",
        {
            "inventory_items": inventory_items,
            "slow_moving_threshold_days": slow_moving_threshold_days,
        },
    )


# ============================================================================
# Product Comparison Tools
# ============================================================================


@tool(approval_mode="never_require")
async def compare_products(
    product_a: Annotated[dict, "製品Aの情報 {'name': str, 'price': float, 'specs': dict}"],
    product_b: Annotated[dict, "製品Bの情報 {'name': str, 'price': float, 'specs': dict}"],
) -> str:
    """2つの製品を比較して比較表を生成します。

    価格、スペック、特徴の差分を表示。
    製品選定や競合分析に使用してください。

    Returns:
        比較表、価格差、優位点を含むJSON
    """
    return await call_mcp_tool("compare_products", {"product_a": product_a, "product_b": product_b})


@tool(approval_mode="never_require")
async def calculate_price_performance(
    price: Annotated[float, "製品価格"],
    performance_score: Annotated[float, "性能スコア（1-100）"],
    product_name: Annotated[str | None, "製品名（オプション）"] = None,
) -> str:
    """価格性能比（コストパフォーマンス）を計算します。

    価格と性能スコアからコスパを評価。
    製品選定や価格設定に使用してください。

    Returns:
        コスパスコア、評価、分析結果を含むJSON
    """
    args = {"price": price, "performance_score": performance_score}
    if product_name:
        args["product_name"] = product_name
    return await call_mcp_tool("calculate_price_performance", args)


@tool(approval_mode="never_require")
async def calculate_bundle_discount(
    products: Annotated[
        list[dict], "購入製品リスト [{'name': str, 'price': float, 'quantity': int}, ...]"
    ],
    discount_rules: Annotated[dict | None, "割引ルール（オプション）"] = None,
) -> str:
    """バンドル購入時の割引を計算します。

    複数商品購入時の割引額を算出。
    セット販売の価格設定やプロモーションに使用してください。

    Returns:
        小計、割引額、最終価格を含むJSON
    """
    args = {"products": products}
    if discount_rules:
        args["discount_rules"] = discount_rules
    return await call_mcp_tool("calculate_bundle_discount", args)


# ============================================================================
# Get all MCP tools for agent
# ============================================================================


def get_mcp_tools() -> list:
    """Get all MCP tools for the agent.

    Returns:
        List of tool functions to add to the agent
    """
    if not MCP_ENABLED:
        logger.info("MCP tools disabled (MCP_ENABLED=false)")
        return []

    return [
        # Sales Analysis
        calculate_yoy_growth,
        calculate_mom_growth,
        calculate_moving_average,
        calculate_abc_analysis,
        calculate_sales_forecast,
        # Customer Segmentation
        calculate_rfm_score,
        classify_customer_segment,
        calculate_clv,
        recommend_next_action,
        # Inventory Analysis
        calculate_inventory_turnover,
        calculate_reorder_point,
        identify_slow_moving_inventory,
        # Product Comparison
        compare_products,
        calculate_price_performance,
        calculate_bundle_discount,
    ]
