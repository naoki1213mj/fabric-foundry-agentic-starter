"""
Multi-Agent Module

This module provides the agent tool handlers for the multi-agent chat system
using Microsoft Agent Framework.

Note: The main orchestration logic is in chat.py using MagenticBuilder.
"""

from .sql_agent import SqlAgentHandler
from .web_agent import WebAgentHandler

__all__ = [
    "SqlAgentHandler",
    "WebAgentHandler",
]
