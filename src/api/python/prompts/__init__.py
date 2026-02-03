"""
Agent Prompts Module

このモジュールは各エージェントのシステムプロンプトを管理します。
chat.pyからプロンプトを分離し、保守性と再利用性を向上させています。

使用方法:
    from prompts import get_sql_agent_prompt, get_web_agent_prompt, get_doc_agent_prompt

    sql_prompt = get_sql_agent_prompt()
    web_prompt = get_web_agent_prompt()
    doc_prompt = get_doc_agent_prompt()
"""

from .doc_agent import DOC_AGENT_DESCRIPTION, DOC_AGENT_PROMPT
from .manager_agent import MANAGER_AGENT_DESCRIPTION, MANAGER_AGENT_PROMPT
from .sql_agent import SQL_AGENT_DESCRIPTION, SQL_AGENT_PROMPT, SQL_AGENT_PROMPT_MINIMAL
from .triage_agent import TRIAGE_AGENT_DESCRIPTION, TRIAGE_AGENT_PROMPT
from .unified_agent import UNIFIED_AGENT_PROMPT
from .web_agent import WEB_AGENT_DESCRIPTION, WEB_AGENT_PROMPT

__all__ = [
    # SQL Agent
    "SQL_AGENT_PROMPT",
    "SQL_AGENT_DESCRIPTION",
    "SQL_AGENT_PROMPT_MINIMAL",
    # Web Agent
    "WEB_AGENT_PROMPT",
    "WEB_AGENT_DESCRIPTION",
    # Doc Agent
    "DOC_AGENT_PROMPT",
    "DOC_AGENT_DESCRIPTION",
    # Manager Agent
    "MANAGER_AGENT_PROMPT",
    "MANAGER_AGENT_DESCRIPTION",
    # Unified Agent
    "UNIFIED_AGENT_PROMPT",
    # Triage Agent
    "TRIAGE_AGENT_PROMPT",
    "TRIAGE_AGENT_DESCRIPTION",
]
