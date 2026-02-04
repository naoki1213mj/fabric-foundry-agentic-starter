#!/usr/bin/env python3
"""
マルチツール統合テストスクリプト

複数のテストシナリオを自動実行し、ツール呼び出しを検証します。
ストリーミングSSEレスポンスに対応。

Usage:
    python scripts/test_multitool.py
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any

import httpx

# テスト設定
API_BASE_URL = "https://api-daj6dri4yf3k3z.azurewebsites.net"
TIMEOUT = 180  # 秒


# テストシナリオ定義
TEST_SCENARIOS = [
    {
        "id": "scenario-1-abc",
        "name": "ABC分析（SQL → MCP）",
        "query": "Mountain Bikeカテゴリの全製品の売上データを取得してABC分析を行ってください。",
        "expected_tools": ["run_sql_query", "calculate_abc_analysis"],
        "difficulty": "中級",
        "reasoning_effort": "low",
    },
    {
        "id": "scenario-2-yoy",
        "name": "YoY成長率分析",
        "query": "2024年と2025年のRoad Bikeカテゴリの売上を比較して、前年同期比成長率（YoY）を計算してください。",
        "expected_tools": ["run_sql_query", "calculate_yoy_growth"],
        "difficulty": "中級",
        "reasoning_effort": "low",
    },
    {
        "id": "scenario-5-doc-minimal",
        "name": "Doc検索（minimal）",
        "query": "Mountain-100の製品仕様を教えてください。",
        "expected_tools": ["search_documents"],
        "difficulty": "初級",
        "reasoning_effort": "minimal",  # Agentic Retrieval直接検索
    },
    {
        "id": "scenario-6-doc-low",
        "name": "Doc検索（low）",
        "query": "Mountain BikeシリーズのサスペンションタイプとフレームSize一覧を教えてください。",
        "expected_tools": ["search_documents"],
        "difficulty": "中級",
        "reasoning_effort": "low",  # シングルパス推論
    },
    {
        "id": "scenario-7-doc-medium",
        "name": "Doc検索（medium）",
        "query": "全製品カテゴリの中で軽量化に優れている製品を仕様書から特定し、比較表を作成してください。",
        "expected_tools": ["search_documents"],
        "difficulty": "上級",
        "reasoning_effort": "medium",  # 反復検索
    },
    {
        "id": "scenario-8-sql-doc",
        "name": "SQL + Doc複合",
        "query": "売上TOP3の製品の仕様を製品仕様書から取得して、売上と仕様の関係を分析してください。",
        "expected_tools": ["run_sql_query", "search_documents"],
        "difficulty": "上級",
        "reasoning_effort": "low",
    },
]

# ツール検出用のインジケーター
TOOL_INDICATORS = {
    "run_sql_query": ["SELECT", "FROM", "売上", "データ", "クエリ", "件", "合計", "製品"],
    "calculate_abc_analysis": ["ABC", "Aランク", "Bランク", "Cランク", "ABC分析", "累積"],
    "calculate_yoy_growth": ["YoY", "前年比", "成長率", "前年同期比", "%", "増加"],
    "calculate_rfm_score": ["RFM", "Recency", "Frequency", "Monetary", "スコア"],
    "classify_customer_segment": ["セグメント", "VIP", "優良顧客", "一般顧客", "分類"],
    "calculate_clv": ["CLV", "顧客生涯価値", "LTV", "価値"],
    "search_documents": [
        "製品仕様", "ドキュメント", "仕様書", "スペック", "仕様", "Specification",
        "フレーム", "サスペンション", "重量", "材質", "Size", "サイズ",
        "knowledge base", "ナレッジベース", "検索結果",
    ],
    "compare_products": ["比較", "vs", "製品比較", "Mountain-100", "Mountain-200"],
    "calculate_price_performance": ["コスパ", "コストパフォーマンス", "価格性能比"],
    "search_web": ["Web", "検索結果", "ニュース", "最新情報", "URL", "http"],
}


async def check_health() -> dict[str, Any]:
    """APIヘルスチェック"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"status": "unhealthy", "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


async def run_chat_query(
    client: httpx.AsyncClient,
    query: str,
    conversation_id: str,
    reasoning_effort: str = "low",
) -> dict[str, Any]:
    """チャットAPIにクエリを送信（ストリーミング対応）"""
    payload = {
        "query": query,
        "conversation_id": conversation_id,
        "agent_mode": "multi_tool",
        "reasoning_effort": reasoning_effort,
    }

    start_time = time.time()
    try:
        # ストリーミングでレスポンスを取得
        # エンドポイントは /api/chat（FastAPIのルーター設定による）
        async with client.stream(
            "POST",
            f"{API_BASE_URL}/api/chat",
            json=payload,
            timeout=TIMEOUT,
        ) as response:
            elapsed = time.time() - start_time

            if response.status_code != 200:
                error_text = await response.aread()
                return {
                    "success": False,
                    "elapsed_seconds": round(elapsed, 2),
                    "error": f"HTTP {response.status_code}: {error_text.decode()[:200]}",
                    "status_code": response.status_code,
                }

            # ストリーミングレスポンスを全て読み取る
            full_response = ""
            chunks = []
            async for chunk in response.aiter_text():
                full_response += chunk
                chunks.append(chunk)

            elapsed = time.time() - start_time
            return {
                "success": True,
                "elapsed_seconds": round(elapsed, 2),
                "full_response": full_response,
                "chunk_count": len(chunks),
                "response_length": len(full_response),
                "status_code": response.status_code,
            }

    except httpx.TimeoutException:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "elapsed_seconds": round(elapsed, 2),
            "error": f"Timeout after {TIMEOUT}s",
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e),
        }


def analyze_tool_usage(response_text: str, expected_tools: list[str]) -> dict[str, Any]:
    """レスポンスからツール使用を推測"""
    detected = []
    missing = []

    for tool in expected_tools:
        indicators = TOOL_INDICATORS.get(tool, [])
        found = any(ind.lower() in response_text.lower() for ind in indicators)
        if found:
            detected.append(tool)
        else:
            missing.append(tool)

    return {
        "expected": expected_tools,
        "detected": detected,
        "missing": missing,
        "coverage": len(detected) / len(expected_tools) if expected_tools else 0,
    }


async def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """単一のテストシナリオを実行"""
    conversation_id = f"test-{scenario['id']}-{uuid.uuid4().hex[:8]}"
    reasoning_effort = scenario.get("reasoning_effort", "low")

    print(f"\n{'='*60}")
    print(f"🧪 {scenario['name']}")
    print(f"   難易度: {scenario['difficulty']}")
    print(f"   reasoning_effort: {reasoning_effort}")
    print(f"   会話ID: {conversation_id}")
    print(f"{'='*60}")
    print(f"📝 クエリ: {scenario['query'][:60]}...")

    result = {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "conversation_id": conversation_id,
        "difficulty": scenario["difficulty"],
        "reasoning_effort": reasoning_effort,
        "query": scenario["query"],
        "success": False,
        "elapsed_seconds": 0,
        "tool_analysis": None,
        "error": None,
    }

    async with httpx.AsyncClient() as client:
        response = await run_chat_query(
            client, scenario["query"], conversation_id, reasoning_effort
        )

        result["elapsed_seconds"] = response.get("elapsed_seconds", 0)

        if response["success"]:
            result["success"] = True
            full_text = response.get("full_response", "")
            result["response_length"] = len(full_text)
            result["chunk_count"] = response.get("chunk_count", 0)

            # ツール使用分析
            result["tool_analysis"] = analyze_tool_usage(
                full_text, scenario["expected_tools"]
            )

            print(f"✅ 成功 ({result['elapsed_seconds']:.1f}秒)")
            print(f"   レスポンス長: {result['response_length']} bytes")
            print(f"   チャンク数: {result['chunk_count']}")
            print(f"   ツールカバレッジ: {result['tool_analysis']['coverage']:.0%}")
            print(f"   検出ツール: {result['tool_analysis']['detected']}")
            if result["tool_analysis"]["missing"]:
                print(f"   未検出ツール: {result['tool_analysis']['missing']}")

            # レスポンスプレビュー（最初の200文字）
            preview = full_text[:200].replace("\n", " ")
            print(f"   プレビュー: {preview}...")
        else:
            result["error"] = response.get("error", "Unknown error")
            print(f"❌ 失敗 ({result['elapsed_seconds']:.1f}秒)")
            print(f"   エラー: {result['error']}")

    return result


async def main():
    """メイン実行"""
    print("=" * 70)
    print("🚀 マルチツール統合テスト開始")
    print(f"   API: {API_BASE_URL}")
    print(f"   タイムアウト: {TIMEOUT}秒")
    print(f"   テストシナリオ数: {len(TEST_SCENARIOS)}")
    print("=" * 70)

    # ヘルスチェック
    health = await check_health()
    print(f"\n🏥 ヘルスチェック: {health.get('status', 'unknown')}")
    if health.get("model"):
        print(f"   モデル: {health['model']}")

    if health.get("status") != "healthy":
        print("❌ APIが利用できません。テストを中止します。")
        return

    # シナリオ実行
    results = []
    total_start = time.time()

    for scenario in TEST_SCENARIOS:
        result = await run_scenario(scenario)
        results.append(result)
        # シナリオ間で少し待機
        await asyncio.sleep(2)

    total_time = time.time() - total_start

    # サマリー表示
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)

    success_count = sum(1 for r in results if r["success"])
    print(f"   総テスト数: {len(results)}")
    print(f"   成功: {success_count}")
    print(f"   失敗: {len(results) - success_count}")
    print(f"   総実行時間: {total_time:.1f}秒")

    print(f"\n{'シナリオ':<30} {'結果':<8} {'時間':<10} {'ツール検証'}")
    print("-" * 70)
    for r in results:
        status = "✅" if r["success"] else "❌"
        tool_coverage = (
            f"{r['tool_analysis']['coverage']:.0%}"
            if r["tool_analysis"]
            else "N/A"
        )
        time_str = f"{r['elapsed_seconds']:.1f}s"
        print(f"{r['scenario_name']:<30} {status:<8} {time_str:<10} {tool_coverage}")

    # レポート保存
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_url": API_BASE_URL,
        "total_scenarios": len(results),
        "success_count": success_count,
        "total_time_seconds": round(total_time, 2),
        "results": results,
    }

    report_path = "test_multitool_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 詳細レポート: {report_path}")

    # トレース確認方法の案内
    print("\n" + "=" * 70)
    print("🔍 トレース確認方法")
    print("=" * 70)
    print("""
1. Azure Portal → Application Insights (appi-daj6dri4yf3k3z)
   → Transaction search → 過去30分のリクエストを検索

2. Kusto クエリ（Log Analytics）:
   traces
   | where timestamp > ago(30m)
   | where message contains "tool" or message contains "agent"
   | order by timestamp desc

3. Azure AI Foundry Portal → Tracing
   → 会話IDでフィルタリング

4. 会話ID一覧:""")
    for r in results:
        print(f"   - {r['conversation_id']}")

    print("\n✨ テスト完了!")


if __name__ == "__main__":
    asyncio.run(main())
