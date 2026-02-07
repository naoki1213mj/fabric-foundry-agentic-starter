## Technical Architecture

**English** | [日本語](./TechnicalArchitecture_JA.md)

This section outlines the components and interactions that powers the unified data analysis platform. The architecture ingests customer information, product details and transaction history and surfaces insights via an interactive web experience.

#### Option 1: Architecture with Microsoft Fabric and Microsoft Copilot Studio:

![image](./Images/ReadMe/solution-architecture-cps.png)

### Customer / product / transaction details
SQL scripts for the customer, product and transaction details are the primary input into the system. These tables are uploaded and stored for downstream insight generation.

### SQL Database in Fabric  
Stores uploaded customer information, product details and transaction history tables. Serves as the primary knowledge source to surface insights in the Fabric Data Agent.

### Fabric Data Agent 
Provides large language model (LLM) capabilities to support naltural language querying. 

### Microsoft Copilot Studio
Fabric Data Agent is connected to an agent in Microsoft Copilot Studio and surfaced as a channel in Microsoft Teams. 

### Microsoft Teams
Users can explore call insights, visualize trends, ask questions in natural language, directly inside Microsoft Teams. 


#### Option 2: Architecture with Microsoft Fabric and Microsoft Foundry:

![image](./Images/ReadMe/solution-architecture.png)

---

## Azure Resource Inventory (Production Environment)

The following resources are deployed in the `<your-resource-group>` resource group:

### Compute & Hosting

| Resource | Type | SKU | Description |
|----------|------|-----|-------------|
| `api-<your-suffix>` | App Service (Linux Container) | - | Python API backend running `da-api:main` from ACR |
| `app-<your-suffix>` | App Service (Linux Container) | - | React frontend running `da-app:main` from ACR |
| `func-mcp-<your-suffix>` | Azure Functions (Linux) | Python 3.12 | MCP Server for business analytics tools |
| `asp-<your-suffix>` | App Service Plan | - | Hosts both App Services |
| `<your-acr-name>` | Container Registry | Premium | Stores Docker images for API and Frontend |

### AI & Machine Learning

| Resource | Type | Models | Description |
|----------|------|--------|-------------|
| `aisa-<your-suffix>` | Azure AI Services | - | Microsoft Foundry hub |
| `aifp-<your-suffix>` | Foundry Project | gpt-5 (500K TPM), gpt-4o-mini (30K TPM), text-embedding-3-large (500K TPM), text-embedding-3-small (120K TPM) | AI model deployments |
| `<your-ai-search-name>` | AI Search | Standard | Foundry IQ knowledge base index (product-specs-kb) |
| Bing Grounding Connection | - | `<your-bing-connection-name>` | Web search via BingGroundingAgentTool |

### Integration & API Management

| Resource | Type | SKU | Description |
|----------|------|-----|-------------|
| `apim-<your-suffix>` | API Management | Consumption | AI Gateway with token metrics, circuit breaker |
| `apic-<your-suffix>` | API Center | Free | Private Tool Catalog for MCP Server discovery |

**Registered APIs in APIM:**

| API Name | Path | Backend | Features |
|----------|------|---------|----------|
| Azure OpenAI API | `/openai` | `aisa-<your-suffix>.openai.azure.com` | Legacy endpoint |
| **Foundry OpenAI API** | `/foundry-openai/openai/v1/` | `aisa-<your-suffix>.services.ai.azure.com` | **Primary endpoint for Responses API** |
| MCP Server API | `/mcp` | `func-mcp-<your-suffix>.azurewebsites.net` | JSON-RPC 2.0 protocol, latency tracking |
| Foundry Agent API | `/foundry-agents` | Foundry Agent Service | Agent responses, timeout handling |

**APIM Policy Configuration:**

```xml
<!-- Inbound: Managed Identity authentication -->
<authentication-managed-identity resource="https://cognitiveservices.azure.com" />

<!-- Backend: Circuit Breaker (30s trip on 429/5xx) -->
<circuit-breaker rule="FoundryCircuitBreaker">
    <trip-duration>PT30S</trip-duration>
    <accepted-count>5</accepted-count>
    <sampling-window>PT10S</sampling-window>
    <trip-threshold percentage="0.5" />
</circuit-breaker>

<!-- Outbound: Token usage headers -->
<set-header name="x-openai-prompt-tokens" exists-action="skip">
    <value>@(context.Response.Headers.GetValueOrDefault("x-ratelimit-remaining-tokens",""))</value>
</set-header>
```

**Registered APIs in API Center:**

| API Name | Tools | Description |
|----------|-------|-------------|
| Business Analytics MCP Server | 16 tools (4 categories) | 売上分析(5), 顧客分析(4), 在庫分析(3), 製品比較(4) |
| Azure OpenAI API | - | Chat Completions, Embeddings endpoints |

### Data Platform

| Resource | Type | SKU | Description |
|----------|------|-----|-------------|
| `<your-fabric-capacity>` | Fabric Capacity | F4 | Fabric compute capacity |
| SQL Database in Fabric | - | - | Customer, Product, Transaction tables + Chat history |

### Observability & Security

| Resource | Type | Description |
|----------|------|-------------|
| `appi-<your-suffix>` | Application Insights | APM, distributed tracing, token metrics |
| `log-<your-suffix>` | Log Analytics Workspace | Centralized logging |
| `id-<your-suffix>` | User Assigned Managed Identity | RBAC for Azure resources |
| `<your-suffix>-backend-app-mi` | User Assigned Managed Identity | Backend app authentication |
| `stmcp<your-suffix>` | Storage Account | MCP Function storage |

---

## Component Details

### Customer / product / transaction details
SQL scripts for the customer, product and transaction details are the primary input into the system. These tables are uploaded and stored for downstream insight generation.

### SQL Database in Fabric  
Stores uploaded customer information, product details and transaction history tables. Serves as the primary knowledge source to surface insights in the web application. And persists chat history and session context for the web interface. Enables retrieval of past interactions.

### Microsoft Foundry
Provides large language model (LLM) capabilities to support natural language querying. Hosts gpt-5 and gpt-4o-mini model deployments for chat completions, and text-embedding-3-large/small for vector embeddings.

### Foundry Agent Service
Provides agent runtime with built-in tools:
- **BingGroundingAgentTool**: Real-time web search using project connection (`<your-bing-connection-name>`)
- **Code Interpreter**: Execute Python code for data analysis
- **Custom tools**: MCP Server integration for business analytics

### Foundry IQ (Agentic Retrieval)
Advanced RAG capabilities with reasoning:
- **Knowledge Base**: `product-specs-kb` - 製品仕様書のナレッジベース
- **Index**: `product-specs-sharepoint-ks-index` - AI Search インデックス
- **Reasoning Effort**: `minimal` (高速) / `low` (バランス) / `medium` (高品質)
- **API Version**: `2025-11-01-preview`

### Agent Framework  
Handles orchestration and intelligent function/tool calling for contextualized responses and multi-step reasoning over retrieved data.

**クライアントパターン:**
- `AzureOpenAIResponsesClient`: Responses API v1 (sql_only, multi_tool モード)
- `AzureOpenAIChatClient`: Chat Completions API (handoff, magentic モード - SDK制約)

### API Management (AI Gateway)
Provides centralized governance for AI APIs:
- **Foundry OpenAI endpoint**: `/foundry-openai/openai/v1/` - Primary endpoint for Responses API
- **Token usage headers**: `x-openai-prompt-tokens`, `x-openai-completion-tokens`, `x-openai-total-tokens`
- **Managed Identity authentication**: Secure access to Foundry services
- **Circuit breaker**: Automatic failover on backend errors (429, 500-599) with 30s trip duration
- **Timeout handling**: Graceful degradation on 408 errors
- **Latency tracking**: `x-gateway-latency-ms` header

> **Note**: `llm-emit-token-metric` policy is not available in Consumption SKU. Token metrics are collected via response headers instead.

### API Center (Private Tool Catalog)
Provides centralized API governance and discovery:
- **MCP Server registration**: Business Analytics MCP Server with 16 tools (4 categories)
  - 売上分析: `calculate_yoy_growth`, `calculate_mom_growth`, `calculate_moving_average`, `calculate_abc_analysis`, `calculate_sales_forecast`
  - 顧客分析: `calculate_rfm_score`, `classify_customer_segment`, `calculate_clv`, `recommend_next_action`
  - 在庫分析: `calculate_inventory_turnover`, `calculate_reorder_point`, `identify_slow_moving_inventory`
  - 製品比較: `compare_products`, `calculate_price_performance`, `suggest_alternatives`, `calculate_bundle_discount`
- **Azure OpenAI registration**: Chat Completions and Embeddings APIs
- **Workspace management**: Default workspace for Agentic AI application

### MCP Server (Azure Functions)
Model Context Protocol server providing 16 business analytics tools (4 categories) via JSON-RPC 2.0:
- 売上分析: `calculate_yoy_growth`, `calculate_mom_growth`, `calculate_moving_average`, `calculate_abc_analysis`, `calculate_sales_forecast`
- 顧客分析: `calculate_rfm_score`, `classify_customer_segment`, `calculate_clv`, `recommend_next_action`
- 在庫分析: `calculate_inventory_turnover`, `calculate_reorder_point`, `identify_slow_moving_inventory`
- 製品比較: `compare_products`, `calculate_price_performance`, `suggest_alternatives`, `calculate_bundle_discount`

### App Service  
Hosts the web application and API layer that interfaces with the AI services and storage layers. Manages user sessions and handles REST calls. Both API and Frontend are containerized and deployed from Azure Container Registry.

### Container Registry  
Stores containerized deployments (da-api, da-app) for use in the hosting environment. Premium tier with geo-replication support.

### Web Front-End  
An interactive UI where users can explore call insights, visualize trends, ask questions in natural language, and generate charts. Connects directly to SQL Database in Fabric and App Services for real-time interaction.

---

## Endpoints

| Service | URL |
|---------|-----|
| Frontend | https://app-<your-suffix>.azurewebsites.net |
| API | https://api-<your-suffix>.azurewebsites.net |
| API Health | https://api-<your-suffix>.azurewebsites.net/health |
| APIM Gateway | https://apim-<your-suffix>.azure-api.net |
| MCP Server | https://func-mcp-<your-suffix>.azurewebsites.net/api/mcp |
