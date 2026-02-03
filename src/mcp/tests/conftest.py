"""
Pytest configuration for MCP Server tests.
"""

import sys
from pathlib import Path

# Add src/mcp to Python path for imports
mcp_path = Path(__file__).parent.parent
if str(mcp_path) not in sys.path:
    sys.path.insert(0, str(mcp_path))
