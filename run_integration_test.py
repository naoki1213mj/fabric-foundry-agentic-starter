"""
Run MCP Integration Test

This script starts the MCP server in background and runs integration tests.
"""

import asyncio
import multiprocessing
import sys
import time


def run_server():
    """Run MCP server in subprocess."""
    import os
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "mcp"))

    import uvicorn
    from local_server import app

    uvicorn.run(app, host="0.0.0.0", port=7071, log_level="warning")


async def run_tests():
    """Run integration tests."""
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "api", "python"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "mcp"))

    os.environ["MCP_SERVER_URL"] = "http://localhost:7071/api/mcp"
    os.environ["MCP_ENABLED"] = "true"

    # Wait for server to start
    import httpx

    for i in range(10):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:7071/api/mcp/health")
                if resp.status_code == 200:
                    print("✅ MCP サーバー起動確認")
                    break
        except Exception:
            print(f"  サーバー起動待機中... ({i + 1}/10)")
            await asyncio.sleep(1)
    else:
        print("❌ MCP サーバーに接続できませんでした")
        return False

    # Import test module
    from test_mcp_integration import test_mcp_integration

    return await test_mcp_integration()


def main():
    """Main function."""
    print("=" * 60)
    print("MCP 統合テスト実行")
    print("=" * 60)

    # Start server in subprocess
    print("\n🚀 MCP サーバーを起動中...")
    server_process = multiprocessing.Process(target=run_server, daemon=True)
    server_process.start()
    time.sleep(2)

    try:
        # Run tests
        success = asyncio.run(run_tests())
        return 0 if success else 1
    finally:
        # Cleanup
        print("\n🛑 サーバーを停止中...")
        server_process.terminate()
        server_process.join(timeout=5)
        print("完了")


if __name__ == "__main__":
    sys.exit(main())
