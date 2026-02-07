"""
Foundry IQ Knowledge Base Setup Script

This script creates:
1. SharePoint Indexed Knowledge Source
2. Knowledge Base for agentic retrieval
3. Project Connection for MCP tool

Prerequisites:
- Microsoft Entra App Registration with:
  - Application permissions: Files.Read.All, Sites.Read.All
  - Admin consent granted
  - Client secret created
- Azure AI Search service with Semantic Ranker enabled
- Azure AI Foundry project

Usage:
    python setup_knowledge_base.py

Environment Variables (or use azd env):
    AI_SEARCH_ENDPOINT: Azure AI Search endpoint
    AI_SEARCH_ADMIN_KEY: Azure AI Search admin key (optional if using RBAC)
    SHAREPOINT_SITE_URL: SharePoint site URL
    SHAREPOINT_APP_ID: Microsoft Entra App ID
    SHAREPOINT_APP_SECRET: Microsoft Entra App client secret
    SHAREPOINT_TENANT_ID: Microsoft Entra tenant ID
    AZURE_AI_AGENT_ENDPOINT: Azure AI Foundry project endpoint
"""

import os
import subprocess
import sys
from typing import Optional

import requests

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Installing required packages...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "azure-identity",
            "azure-ai-projects",
            "requests",
        ],
        check=True,
    )
    from azure.identity import DefaultAzureCredential


# Configuration
SEARCH_SERVICE_NAME = os.environ.get("AI_SEARCH_SERVICE_NAME", "<your-ai-search-name>")
SEARCH_ENDPOINT = os.environ.get("AI_SEARCH_ENDPOINT", f"https://{SEARCH_SERVICE_NAME}.search.windows.net")
SHAREPOINT_SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "<your-sharepoint-site-url>")
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "<your-tenant-id>")

# Knowledge Source and Base names
KNOWLEDGE_SOURCE_NAME = "product-specs-sharepoint-ks"
KNOWLEDGE_BASE_NAME = "product-specs-kb"

# API Version for agentic retrieval
API_VERSION = "2025-11-01-preview"


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


def get_search_admin_key() -> str:
    """Get Azure AI Search admin key."""
    # Try environment variable first
    key = os.environ.get("AI_SEARCH_ADMIN_KEY") or get_azd_env_value(
        "AI_SEARCH_ADMIN_KEY"
    )
    if key:
        return key

    # Try Azure CLI
    try:
        result = subprocess.run(
            [
                "az",
                "search",
                "admin-key",
                "show",
                "--service-name",
                SEARCH_SERVICE_NAME,
                "--resource-group",
                get_azd_env_value("AZURE_RESOURCE_GROUP") or "",
                "--query",
                "primaryKey",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Failed to get search admin key: {e}")
        print("Please set AI_SEARCH_ADMIN_KEY environment variable")
        sys.exit(1)


def get_sharepoint_credentials() -> tuple[str, str]:
    """Get SharePoint app credentials."""
    app_id = os.environ.get("SHAREPOINT_APP_ID") or get_azd_env_value(
        "SHAREPOINT_APP_ID"
    )
    app_secret = os.environ.get("SHAREPOINT_APP_SECRET") or get_azd_env_value(
        "SHAREPOINT_APP_SECRET"
    )

    if not app_id or not app_secret:
        print("\n⚠️  SharePoint credentials not found!")
        print("Please set the following environment variables:")
        print("  - SHAREPOINT_APP_ID: Microsoft Entra App ID")
        print("  - SHAREPOINT_APP_SECRET: Microsoft Entra App client secret")
        print("\nOr run: azd env set SHAREPOINT_APP_ID <value>")
        print("        azd env set SHAREPOINT_APP_SECRET <value>")
        sys.exit(1)

    return app_id, app_secret


def check_existing_knowledge_sources(headers: dict) -> list:
    """List existing knowledge sources."""
    url = f"{SEARCH_ENDPOINT}/knowledgesources?api-version={API_VERSION}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    return []


def create_sharepoint_knowledge_source(
    headers: dict, app_id: str, app_secret: str
) -> dict:
    """Create SharePoint indexed knowledge source."""
    url = f"{SEARCH_ENDPOINT}/knowledgesources/{KNOWLEDGE_SOURCE_NAME}?api-version={API_VERSION}"

    # Connection string for SharePoint
    connection_string = (
        f"SharePointOnlineEndpoint={SHAREPOINT_SITE_URL};"
        f"ApplicationId={app_id};"
        f"ApplicationSecret={app_secret};"
        f"TenantId={TENANT_ID}"
    )

    # Get embedding model endpoint from azd env
    ai_agent_endpoint = (
        os.environ.get("AZURE_AI_AGENT_ENDPOINT")
        or get_azd_env_value("AZURE_AI_AGENT_ENDPOINT")
        or ""
    )
    # Extract OpenAI endpoint from Foundry endpoint
    # Format: https://aisa-xxx.services.ai.azure.com/api/projects/xxx
    # OpenAI: https://aisa-xxx.openai.azure.com
    import re

    match = re.match(r"https://([^.]+)\.services\.ai\.azure\.com", ai_agent_endpoint)
    openai_resource_uri = f"https://{match.group(1)}.openai.azure.com" if match else ""

    body = {
        "name": KNOWLEDGE_SOURCE_NAME,
        "kind": "indexedSharePoint",
        "description": "Product specifications from SharePoint",
        "indexedSharePointParameters": {
            "connectionString": connection_string,
            "containerName": "defaultSiteLibrary",
            "query": None,
            "ingestionParameters": {
                "contentExtractionMode": "minimal",
                "embeddingModel": {
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": openai_resource_uri,
                        "deploymentId": "text-embedding-3-large",
                        "modelName": "text-embedding-3-large",
                    },
                },
            },
        },
    }

    print(f"\n📦 Creating Knowledge Source: {KNOWLEDGE_SOURCE_NAME}")
    response = requests.put(url, headers=headers, json=body)

    if response.status_code in [200, 201, 204]:
        print("   ✅ Knowledge Source created successfully")
        if response.status_code == 204:
            return {"name": KNOWLEDGE_SOURCE_NAME, "status": "created"}
        return response.json()
    else:
        print(f"   ❌ Failed to create Knowledge Source: {response.status_code}")
        print(f"   Error: {response.text}")
        return {}


def check_knowledge_source_status(headers: dict) -> dict:
    """Check knowledge source ingestion status."""
    url = f"{SEARCH_ENDPOINT}/knowledgesources/{KNOWLEDGE_SOURCE_NAME}?api-version={API_VERSION}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return {}


def create_knowledge_base(
    headers: dict, model_deployment: str, foundry_project_endpoint: str
) -> dict:
    """Create knowledge base for agentic retrieval."""
    url = f"{SEARCH_ENDPOINT}/knowledgebases/{KNOWLEDGE_BASE_NAME}?api-version={API_VERSION}"

    # Extract OpenAI endpoint from Foundry endpoint
    import re

    match = re.match(
        r"https://([^.]+)\.services\.ai\.azure\.com", foundry_project_endpoint
    )
    openai_resource_uri = f"https://{match.group(1)}.openai.azure.com" if match else ""

    body = {
        "name": KNOWLEDGE_BASE_NAME,
        "description": "Product specifications knowledge base for RAG",
        "knowledgeSources": [{"name": KNOWLEDGE_SOURCE_NAME}],
        "outputMode": "extractiveData",  # Recommended for Foundry Agent Service
        "retrievalReasoningEffort": {
            "kind": "minimal"  # Reduces latency and cost
        },
        "models": [
            {
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": openai_resource_uri,
                    "deploymentId": model_deployment,
                    "modelName": model_deployment,
                },
            }
        ],
    }

    print(f"\n📚 Creating Knowledge Base: {KNOWLEDGE_BASE_NAME}")
    response = requests.put(url, headers=headers, json=body)

    if response.status_code in [200, 201]:
        print("   ✅ Knowledge Base created successfully")
        kb_data = response.json()
        mcp_endpoint = f"{SEARCH_ENDPOINT}/knowledgebases/{KNOWLEDGE_BASE_NAME}/mcp?api-version={API_VERSION}"
        print(f"   📡 MCP Endpoint: {mcp_endpoint}")
        return kb_data
    else:
        print(f"   ❌ Failed to create Knowledge Base: {response.status_code}")
        print(f"   Error: {response.text}")
        return {}


def create_project_connection(project_endpoint: str, mcp_endpoint: str) -> dict:
    """Create project connection for MCP tool."""
    credential = DefaultAzureCredential()

    # Get management token
    token = credential.get_token("https://management.azure.com/.default")
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }

    # Extract project resource ID from endpoint
    # Format: https://<account>.services.ai.azure.com/api/projects/<project>
    # Need: /subscriptions/.../providers/Microsoft.MachineLearningServices/workspaces/<account>/projects/<project>

    subscription_id = get_azd_env_value("AZURE_SUBSCRIPTION_ID")
    resource_group = get_azd_env_value("AZURE_RESOURCE_GROUP")

    if not subscription_id or not resource_group:
        print(
            "\n⚠️  Cannot create project connection: missing subscription or resource group"
        )
        print("Please run this step manually in Azure Portal")
        return {}

    # Parse endpoint to get account and project names
    # Example: https://aisa-xxx.services.ai.azure.com/api/projects/aiproj-xxx
    import re

    match = re.match(
        r"https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)",
        project_endpoint,
    )
    if not match:
        print(f"\n⚠️  Cannot parse project endpoint: {project_endpoint}")
        return {}

    account_name = match.group(1)
    project_name = match.group(2)

    project_resource_id = (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{account_name}"
        f"/projects/{project_name}"
    )

    connection_name = "kb-mcp-connection"
    url = f"https://management.azure.com{project_resource_id}/connections/{connection_name}?api-version=2025-10-01-preview"

    body = {
        "name": connection_name,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": mcp_endpoint,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"},
        },
    }

    print(f"\n🔗 Creating Project Connection: {connection_name}")
    response = requests.put(url, headers=headers, json=body)

    if response.status_code in [200, 201]:
        print("   ✅ Project Connection created successfully")
        return response.json()
    else:
        print(f"   ❌ Failed to create Project Connection: {response.status_code}")
        print(f"   Error: {response.text}")
        return {}


def update_environment_variables(mcp_endpoint: str, connection_name: str):
    """Update azd environment with knowledge base settings."""
    print("\n📝 Updating environment variables...")

    env_vars = {
        "AI_SEARCH_ENDPOINT": SEARCH_ENDPOINT,
        "AI_SEARCH_KNOWLEDGE_BASE_NAME": KNOWLEDGE_BASE_NAME,
        "AI_SEARCH_PROJECT_CONNECTION_NAME": connection_name or "kb-mcp-connection",
        "AI_SEARCH_MCP_ENDPOINT": mcp_endpoint,
    }

    for key, value in env_vars.items():
        try:
            subprocess.run(
                ["azd", "env", "set", key, value], check=True, capture_output=True
            )
            print(f"   ✅ {key}={value}")
        except subprocess.CalledProcessError:
            print(f"   ⚠️  Failed to set {key} (set manually if needed)")


def main():
    print("=" * 60)
    print("🚀 Foundry IQ Knowledge Base Setup")
    print("=" * 60)
    print("\nConfiguration:")
    print(f"  Search Service: {SEARCH_SERVICE_NAME}")
    print(f"  SharePoint Site: {SHAREPOINT_SITE_URL}")
    print(f"  Tenant ID: {TENANT_ID}")

    # Get credentials
    app_id, app_secret = get_sharepoint_credentials()
    print(f"  SharePoint App ID: {app_id[:8]}...")

    # Get search admin key
    search_key = get_search_admin_key()
    headers = {"api-key": search_key, "Content-Type": "application/json"}

    # Check existing knowledge sources
    print("\n🔍 Checking existing Knowledge Sources...")
    existing = check_existing_knowledge_sources(headers)
    for ks in existing:
        print(f"   - {ks.get('name')} ({ks.get('type', 'unknown')})")

    # Create knowledge source
    ks_result = create_sharepoint_knowledge_source(headers, app_id, app_secret)

    if not ks_result:
        print("\n❌ Failed to create Knowledge Source. Exiting.")
        sys.exit(1)

    # Get Foundry project endpoint
    project_endpoint = os.environ.get("AZURE_AI_AGENT_ENDPOINT") or get_azd_env_value(
        "AZURE_AI_AGENT_ENDPOINT"
    )
    model_deployment = (
        os.environ.get("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
        or get_azd_env_value("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
        or "gpt-4o"
    )

    if not project_endpoint:
        print("\n⚠️  AZURE_AI_AGENT_ENDPOINT not set. Skipping Knowledge Base creation.")
        print("Set it and run this script again to create the Knowledge Base.")
        sys.exit(0)

    # Create knowledge base
    kb_result = create_knowledge_base(headers, model_deployment, project_endpoint)

    if kb_result:
        mcp_endpoint = f"{SEARCH_ENDPOINT}/knowledgebases/{KNOWLEDGE_BASE_NAME}/mcp?api-version={API_VERSION}"

        # Create project connection
        conn_result = create_project_connection(project_endpoint, mcp_endpoint)

        # Update environment variables
        update_environment_variables(mcp_endpoint, "kb-mcp-connection")

        print("\n" + "=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Wait for SharePoint indexing to complete (check Azure Portal)")
        print("2. Run: python create_agents.py  (to recreate agents with DocAgent)")
        print("3. Deploy: azd deploy")
        print(f"\nMCP Endpoint: {mcp_endpoint}")
    else:
        print("\n⚠️  Knowledge Base creation failed. Check the errors above.")


if __name__ == "__main__":
    main()
