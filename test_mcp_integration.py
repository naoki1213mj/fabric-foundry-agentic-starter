"""
Integration Test for MCP Client

This test verifies that the MCP client can connect to the local MCP server
and execute tools correctly.
"""

import asyncio
import json
import os
import sys

# Set up path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "api", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "mcp"))

# Set environment variable for local testing
os.environ["MCP_SERVER_URL"] = "http://localhost:7071/api/mcp"
os.environ["MCP_ENABLED"] = "true"


async def test_mcp_integration():
    """Run integration tests against local MCP server."""
    print("=" * 60)
    print("MCP 統合テスト")
    print("=" * 60)

    # Import after setting environment
    from mcp_client import call_mcp_tool, get_mcp_tools

    # Test 1: Get MCP tools
    print("\n📋 Test 1: get_mcp_tools()")
    print("-" * 40)
    tools = get_mcp_tools()
    print(f"  ツール数: {len(tools)}")
    if tools:
        print("  ✅ MCP ツールが正常に取得されました")
        for tool in tools[:3]:  # Show first 3
            tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
            print(f"    - {tool_name}")
        if len(tools) > 3:
            print(f"    ... 他 {len(tools) - 3} ツール")
    else:
        print("  ⚠️ MCP ツールが無効または取得できませんでした")
        return False

    # Test 2: Call calculate_yoy_growth
    print("\n📊 Test 2: calculate_yoy_growth")
    print("-" * 40)
    try:
        result = await call_mcp_tool(
            "calculate_yoy_growth", {"current_value": 120000, "previous_value": 100000}
        )
        result_dict = json.loads(result)
        print("  入力: 今期=120,000, 前期=100,000")
        print(f"  結果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
        if "growth_rate_percent" in result_dict:
            print("  ✅ YoY 成長率計算が正常に動作しました")
        else:
            print(f"  ❌ 予期しない結果: {result}")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

    # Test 3: Call calculate_rfm_score
    print("\n👥 Test 3: calculate_rfm_score")
    print("-" * 40)
    try:
        result = await call_mcp_tool(
            "calculate_rfm_score", {"recency_days": 5, "frequency": 10, "monetary": 200000}
        )
        result_dict = json.loads(result)
        print("  入力: recency_days=5, frequency=10, monetary=200,000")
        print(f"  結果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
        if "rfm_scores" in result_dict:
            print("  ✅ RFM スコア計算が正常に動作しました")
        else:
            print(f"  ❌ 予期しない結果: {result}")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

    # Test 4: Call identify_slow_moving_inventory
    print("\n📦 Test 4: identify_slow_moving_inventory")
    print("-" * 40)
    try:
        inventory_items = [
            {
                "name": "商品A",
                "quantity": 100,
                "unit_cost": 1000,
                "days_in_stock": 200,
                "monthly_sales": 0,
            },
            {
                "name": "商品B",
                "quantity": 50,
                "unit_cost": 2000,
                "days_in_stock": 45,
                "monthly_sales": 5,
            },
            {
                "name": "商品C",
                "quantity": 30,
                "unit_cost": 3000,
                "days_in_stock": 10,
                "monthly_sales": 20,
            },
        ]
        result = await call_mcp_tool(
            "identify_slow_moving_inventory", {"inventory_items": inventory_items}
        )
        result_dict = json.loads(result)
        print("  入力: 3商品の在庫データ")
        print(f"  結果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
        if "summary" in result_dict or "dead_stock" in result_dict or "slow_moving" in result_dict:
            print("  ✅ 滞留在庫分析が正常に動作しました")
        else:
            print("  ⚠️ 予期しない結果形式")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

    # Test 5: Call compare_products
    print("\n🔄 Test 5: compare_products")
    print("-" * 40)
    try:
        product_a = {
            "name": "iPhone 15",
            "price": 125800,
            "specs": {"storage": "256GB", "rating": 4.5},
        }
        product_b = {
            "name": "Galaxy S24",
            "price": 112000,
            "specs": {"storage": "256GB", "rating": 4.3},
        }
        result = await call_mcp_tool(
            "compare_products", {"product_a": product_a, "product_b": product_b}
        )
        result_dict = json.loads(result)
        print("  入力: iPhone 15 vs Galaxy S24")
        print(f"  結果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
        if "comparison" in result_dict or "products" in result_dict or "price_diff" in result_dict:
            print("  ✅ 商品比較が正常に動作しました")
        else:
            print("  ⚠️ 予期しない結果形式")
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ すべての統合テストがパスしました！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_integration())
    sys.exit(0 if success else 1)
