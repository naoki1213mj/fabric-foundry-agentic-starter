"""
Agent Management Script - Refactored Version

This script creates or updates Microsoft Foundry agents using external configuration files.
Supports modular instructions, tools, and schema definitions.

Usage:
    python create_agents.py --ai_project_endpoint "..." --solution_name "..." --gpt_model_name "..." --usecase "retail"

Or with azd environment:
    python create_agents.py  # Uses azd env get-values automatically
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add parent directory to path for shared utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ApproximateLocation,
    BingGroundingAgentTool,
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    FunctionTool,
    PromptAgentDefinition,
    WebSearchPreviewTool,
)
from azure_credential_utils import get_azure_credential


class AgentManager:
    """Manages Microsoft Foundry agent creation and updates."""

    def __init__(self, config_path: str = None):
        """Initialize with configuration file path."""
        self.script_dir = Path(__file__).parent
        self.config_path = config_path or self.script_dir / "config.yaml"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration file."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_yaml(self, relative_path: str) -> Dict[str, Any]:
        """Load a YAML file relative to script directory."""
        full_path = self.script_dir / relative_path
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_instructions(self, relative_path: str) -> str:
        """Load instructions from markdown file."""
        full_path = self.script_dir / relative_path
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_tables_schema(self, usecase: str) -> str:
        """Load and format table schema for the given use case."""
        usecase_config = self.config["usecases"].get(usecase)
        if not usecase_config:
            raise ValueError(f"Unknown usecase: {usecase}")

        tables_path = self.script_dir / usecase_config["tables_file"]
        with open(tables_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        schema_format = usecase_config.get("schema_format", "simple")
        return self._format_tables_schema(data, schema_format)

    def _format_tables_schema(self, data: Dict, schema_format: str) -> str:
        """Format table schema based on the specified format."""
        tables_str = ""
        for i, table in enumerate(data.get("tables", []), 1):
            tablename = table.get("tablename", "")
            columns = table.get("columns", [])

            if schema_format == "detailed":
                # Insurance format: column name (title)
                col_str = ", ".join(
                    f"{col['name']} ({col['title']})"
                    if isinstance(col, dict)
                    else str(col)
                    for col in columns
                )
                tables_str += (
                    f"\n {i}. Table: dbo.{tablename}\n        Columns: {col_str}"
                )
            else:
                # Retail format: simple column list
                col_str = ", ".join(str(col) for col in columns)
                tables_str += (
                    f"\n {i}.Table:dbo.{tablename}\n        Columns: {col_str}"
                )

        return tables_str

    def _build_tools(self, tools_config: List[Dict]) -> List:
        """Build tool objects from configuration.

        Handles FunctionTool, WebSearchPreviewTool, and BingGroundingAgentTool based on tool type.
        Note: WebSearchPreviewTool is recommended for gpt-5 models as BingGroundingAgentTool
        does not support gpt-5.
        """
        tools = []
        for tool_def in tools_config:
            tool_type = tool_def.get("type", "function")

            if tool_type == "web_search_preview":
                # Use official WebSearchPreviewTool - recommended for gpt-5
                # No additional Azure resources required (managed by Microsoft)
                user_location_config = tool_def.get("user_location", {})
                user_location = ApproximateLocation(
                    country=user_location_config.get("country", "JP"),
                    city=user_location_config.get("city", "Tokyo"),
                    region=user_location_config.get("region", "Kanto"),
                )
                tools.append(WebSearchPreviewTool(user_location=user_location))
                print("  → Web Search Preview tool configured (recommended for gpt-5)")
            elif tool_type == "bing_grounding":
                # Use official BingGroundingAgentTool pattern
                bing_connection_name = tool_def.get(
                    "connection_name", os.environ.get("BING_CONNECTION_NAME", "")
                )
                if not bing_connection_name:
                    print("  ⚠ Skipping bing_grounding: BING_CONNECTION_NAME not set")
                    continue

                # Get Bing connection ID from Microsoft Foundry
                # This will be resolved at agent creation time
                tools.append(
                    {"_bing_grounding": True, "connection_name": bing_connection_name}
                )
                print(
                    f"  → Bing Grounding configured with connection: {bing_connection_name}"
                )
            elif tool_type == "mcp_knowledge_base":
                # MCP Knowledge Base tool - handled at runtime in chat.py
                # The agent will use the MCP endpoint configured in environment
                print("  → MCP Knowledge Base tool configured (handled at runtime)")
                # Skip adding to tools - MCP is configured via project connection
                continue
            else:
                # Standard FunctionTool - requires name field
                if "name" not in tool_def:
                    print(f"  ⚠ Skipping tool without name: {tool_def}")
                    continue
                tools.append(
                    FunctionTool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        parameters=tool_def["parameters"],
                    )
                )
        return tools

    def create_agents(
        self,
        ai_project_endpoint: str,
        solution_name: str,
        gpt_model_name: str,
        usecase: str,
    ) -> Dict[str, str]:
        """Create or update all configured agents."""
        # Normalize usecase (case-insensitive)
        usecase = usecase.lower()
        if usecase in ("retail-sales-analysis", "retail"):
            usecase = "retail"
        elif usecase in ("insurance", "insurance-analysis"):
            usecase = "insurance"

        # Load table schema
        tables_schema = self._load_tables_schema(usecase)

        # Also update the shared tables.json for backward compatibility
        self._update_shared_tables_json(usecase)

        # Connect to Microsoft Foundry
        project_client = AIProjectClient(
            endpoint=ai_project_endpoint,
            credential=get_azure_credential(),
        )

        results = {}

        with project_client:
            for agent_key, agent_config in self.config["agents"].items():
                # Load instructions
                instructions = self._load_instructions(
                    agent_config["instructions_file"]
                )

                # Replace placeholders
                placeholder = agent_config.get("settings", {}).get(
                    "tables_schema_placeholder"
                )
                if placeholder and placeholder in instructions:
                    instructions = instructions.replace(placeholder, tables_schema)

                # Load tools
                tools_config = self._load_yaml(agent_config["tools_file"])
                raw_tools = self._build_tools(tools_config.get("tools", []))

                # Process tools - resolve BingGroundingAgentTool
                final_tools = []
                for tool in raw_tools:
                    if isinstance(tool, dict) and tool.get("_bing_grounding"):
                        # Resolve Bing connection and create BingGroundingAgentTool
                        connection_name = tool["connection_name"]
                        try:
                            bing_connection = project_client.connections.get(
                                connection_name
                            )
                            bing_tool = BingGroundingAgentTool(
                                bing_grounding=BingGroundingSearchToolParameters(
                                    search_configurations=[
                                        BingGroundingSearchConfiguration(
                                            project_connection_id=bing_connection.id
                                        )
                                    ]
                                )
                            )
                            final_tools.append(bing_tool)
                            print("  → Added BingGroundingAgentTool")
                        except Exception as e:
                            print(
                                f"  ⚠ Failed to get Bing connection '{connection_name}': {e}"
                            )
                    else:
                        final_tools.append(tool)

                # Create agent name
                agent_name = f"{agent_config['name_prefix']}-{solution_name}"

                # Create or update agent
                print(f"Creating/updating agent: {agent_name}")
                agent = project_client.agents.create_version(
                    agent_name=agent_name,
                    definition=PromptAgentDefinition(
                        model=gpt_model_name,
                        instructions=instructions,
                        tools=final_tools if final_tools else None,
                    ),
                )

                results[agent_key] = agent.name
                print(f"  ✓ {agent_key}: {agent.name}")

        return results

    def _update_shared_tables_json(self, usecase: str) -> None:
        """Update shared tables.json for backward compatibility."""
        usecase_config = self.config["usecases"].get(usecase)
        if not usecase_config:
            return

        source_path = self.script_dir / usecase_config["tables_file"]
        dest_path = self.script_dir.parent / "fabric_scripts" / "data" / "tables.json"

        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


def get_azd_env_value(key: str) -> Optional[str]:
    """Get value from azd environment."""
    try:
        result = subprocess.run(
            ["azd", "env", "get-value", key],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create or update Microsoft Foundry agents"
    )
    parser.add_argument(
        "--ai_project_endpoint", help="Microsoft Foundry project endpoint"
    )
    parser.add_argument("--solution_name", help="Solution name suffix for agent names")
    parser.add_argument("--gpt_model_name", help="GPT model deployment name")
    parser.add_argument("--usecase", help="Use case (retail or insurance)")
    parser.add_argument("--config", help="Path to config.yaml", default=None)

    args = parser.parse_args()

    # Get values from args or azd environment
    ai_project_endpoint = args.ai_project_endpoint or get_azd_env_value(
        "AZURE_AI_AGENT_ENDPOINT"
    )
    solution_name = args.solution_name or get_azd_env_value("SOLUTION_NAME")
    gpt_model_name = args.gpt_model_name or get_azd_env_value(
        "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    )
    usecase = args.usecase or get_azd_env_value("USE_CASE") or "retail"

    # Validate required parameters
    if not all([ai_project_endpoint, solution_name, gpt_model_name]):
        print(
            "Error: Missing required parameters. Please provide via arguments or azd environment."
        )
        print(f"  ai_project_endpoint: {ai_project_endpoint or 'MISSING'}")
        print(f"  solution_name: {solution_name or 'MISSING'}")
        print(f"  gpt_model_name: {gpt_model_name or 'MISSING'}")
        sys.exit(1)

    # Create agents
    manager = AgentManager(args.config)
    results = manager.create_agents(
        ai_project_endpoint=ai_project_endpoint,
        solution_name=solution_name,
        gpt_model_name=gpt_model_name,
        usecase=usecase,
    )

    # Output for shell script consumption (multi-agent)
    print(f"\norchestratorAgentName={results.get('orchestrator_agent', '')}")
    print(f"sqlAgentName={results.get('sql_agent', '')}")
    print(f"webAgentName={results.get('web_agent', '')}")
    print(f"docAgentName={results.get('doc_agent', '')}")
    print(f"titleAgentName={results.get('title_agent', '')}")
    # Legacy compatibility
    print(f"chatAgentName={results.get('sql_agent', results.get('chat_agent', ''))}")


if __name__ == "__main__":
    main()
