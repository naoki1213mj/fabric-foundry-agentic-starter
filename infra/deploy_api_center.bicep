// Azure API Center for Private Tool Catalog
// Enables MCP Server discovery and governance in Microsoft Foundry
// Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/private-tool-catalog

param location string = resourceGroup().location
param solutionName string

@description('MCP Server Function App default hostname')
param mcpServerHostname string = ''

@description('API Management Gateway URL')
param apimGatewayUrl string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var apiCenterName = '${abbrs.integration.apiCenter}${solutionName}'

// Azure API Center Resource
resource apiCenter 'Microsoft.ApiCenter/services@2024-03-01' = {
  name: apiCenterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
  tags: {
    environment: 'hackathon'
    purpose: 'mcp-tool-catalog'
    workload: 'agentic-ai'
  }
}

// Default Workspace (required for API registration)
resource workspace 'Microsoft.ApiCenter/services/workspaces@2024-03-01' = {
  parent: apiCenter
  name: 'default'
  properties: {
    title: 'Default Workspace'
    description: 'Default workspace for Agentic AI application APIs and MCP servers'
  }
}

// Environment for Production
resource prodEnvironment 'Microsoft.ApiCenter/services/workspaces/environments@2024-03-01' = {
  parent: workspace
  name: 'production'
  properties: {
    title: 'Production'
    description: 'Production environment for Agentic AI application'
    kind: 'production'
    server: {
      type: 'Azure API Management'
      managementPortalUri: [
        apimGatewayUrl
      ]
    }
  }
}

// Register MCP Server API in API Center
resource mcpServerApi 'Microsoft.ApiCenter/services/workspaces/apis@2024-03-01' = if (!empty(mcpServerHostname)) {
  parent: workspace
  name: 'mcp-business-analytics'
  properties: {
    title: 'Business Analytics MCP Server'
    description: '''
      Model Context Protocol (MCP) Server providing business analytics tools for AI agents.

      Available Tools:
      - calculate_yoy_growth: Calculate year-over-year growth rates
      - calculate_rfm_score: Customer segmentation using RFM analysis
      - identify_slow_moving_inventory: Inventory analysis for slow-moving products
      - compare_products: Compare multiple products across various metrics
      - analyze_customer_segment: Detailed customer segment analysis
    '''
    kind: 'rest'
    termsOfService: {
      url: 'https://github.com/naoki1213mj/hackathon202601-stu-se-agentic-ai'
    }
    contacts: [
      {
        name: 'Agentic AI Team'
        email: 'hackathon@contoso.com'
      }
    ]
    customProperties: {
      mcpProtocolVersion: '2024-11-05'
      toolCount: '5'
      category: 'Business Analytics'
    }
  }
}

// API Version for MCP Server
resource mcpServerApiVersion 'Microsoft.ApiCenter/services/workspaces/apis/versions@2024-03-01' = if (!empty(mcpServerHostname)) {
  parent: mcpServerApi
  name: 'version-1-0'
  properties: {
    title: 'Version 1.0'
    lifecycleStage: 'production'
  }
}

// API Definition (OpenAPI spec reference - MCP protocol doesn't have OpenAPI, but we can reference JSON-RPC schema)
resource mcpServerApiDefinition 'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions@2024-03-01' = if (!empty(mcpServerHostname)) {
  parent: mcpServerApiVersion
  name: 'mcp-jsonrpc'
  properties: {
    title: 'MCP JSON-RPC 2.0 Protocol'
    description: 'Model Context Protocol using JSON-RPC 2.0 messaging format'
  }
}

// MCP Server Deployment Configuration
resource mcpServerDeployment 'Microsoft.ApiCenter/services/workspaces/apis/deployments@2024-03-01' = if (!empty(mcpServerHostname)) {
  parent: mcpServerApi
  name: 'production-deployment'
  properties: {
    title: 'Production Deployment'
    description: 'MCP Server deployed via Azure Functions with API Management gateway'
    environmentId: prodEnvironment.id
    definitionId: mcpServerApiDefinition.id
    state: 'active'
    server: {
      runtimeUri: [
        'https://${mcpServerHostname}/api/mcp'
        !empty(apimGatewayUrl) ? '${apimGatewayUrl}/mcp' : ''
      ]
    }
  }
}

// Azure OpenAI API Registration
resource aoaiApi 'Microsoft.ApiCenter/services/workspaces/apis@2024-03-01' = if (!empty(apimGatewayUrl)) {
  parent: workspace
  name: 'azure-openai'
  properties: {
    title: 'Azure OpenAI API'
    description: '''
      Azure OpenAI Service endpoints proxied through API Management AI Gateway.

      Features:
      - Chat Completions (gpt-5, gpt-4o-mini)
      - Embeddings (text-embedding-3-large, text-embedding-3-small)
      - Managed Identity authentication
      - Token usage metering
    '''
    kind: 'rest'
  }
}

// Outputs
output apiCenterName string = apiCenter.name
output apiCenterId string = apiCenter.id
output apiCenterIdentityPrincipalId string = apiCenter.identity.principalId
output workspaceId string = workspace.id
output mcpServerApiId string = !empty(mcpServerHostname) ? mcpServerApi.id : ''
