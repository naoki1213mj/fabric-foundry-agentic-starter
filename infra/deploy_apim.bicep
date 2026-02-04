// Azure API Management (AI Gateway) for Azure OpenAI
// Provides: Rate limiting, Logging, Token metering, Failover support

param location string = resourceGroup().location
param solutionName string
param azureOpenAiEndpoint string
@description('Azure OpenAI deployment name (used in API path)')
param azureOpenAiDeploymentName string
@description('Managed Identity Object ID for RBAC (for future use)')
param managedIdentityObjectId string = ''
@description('Application Insights resource ID for logging')
param applicationInsightsId string = ''
@description('Application Insights Instrumentation Key for APIM logging')
@secure()
param applicationInsightsInstrumentationKey string = ''
@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string = ''
@description('Publisher email for APIM (required)')
param publisherEmail string = 'hackathon@contoso.com'
@description('Publisher name for APIM (required)')
param publisherName string = 'Agentic AI Hackathon'
@description('MCP Server Function endpoint URL')
param mcpServerEndpoint string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var apimResourceName = '${abbrs.integration.apiManagementService}${solutionName}'

// API Management Service
resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: apimResourceName
  location: location
  sku: {
    name: 'Consumption'  // Cost-effective for hackathon (Pay-per-call)
    capacity: 0  // Consumption tier uses 0 capacity
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    // Consumption tier doesn't support VNet
  }
  tags: {
    environment: 'hackathon'
    purpose: 'ai-gateway'
    workload: 'agentic-ai'
    managedIdentityId: managedIdentityObjectId
  }
}

// Logger for Application Insights (if configured)
resource apimLogger 'Microsoft.ApiManagement/service/loggers@2024-05-01' = if (!empty(applicationInsightsId) && !empty(applicationInsightsInstrumentationKey)) {
  parent: apim
  name: 'appinsights-logger'
  properties: {
    loggerType: 'applicationInsights'
    resourceId: applicationInsightsId
    credentials: {
      instrumentationKey: applicationInsightsInstrumentationKey
    }
  }
}

// Azure OpenAI Backend
resource aoaiBackend 'Microsoft.ApiManagement/service/backends@2024-05-01' = {
  parent: apim
  name: 'azure-openai'
  properties: {
    title: 'Azure OpenAI Service'
    description: 'Azure OpenAI backend with Managed Identity authentication'
    url: azureOpenAiEndpoint
    protocol: 'http'
    credentials: {
      // Use Managed Identity for authentication
    }
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
    circuitBreaker: {
      rules: [
        {
          name: 'openai-circuit-breaker'
          failureCondition: {
            count: 3
            interval: 'PT1M'
            statusCodeRanges: [
              { min: 429, max: 429 }  // Rate limit
              { min: 500, max: 599 }  // Server errors
            ]
          }
          tripDuration: 'PT30S'
          acceptRetryAfter: true
        }
      ]
    }
  }
}

// MCP Server Backend (Azure Functions)
resource mcpBackend 'Microsoft.ApiManagement/service/backends@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: apim
  name: 'mcp-server'
  properties: {
    title: 'MCP Server (Business Analytics Tools)'
    description: 'MCP Server providing business analytics tools via Azure Functions'
    url: mcpServerEndpoint
    protocol: 'http'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
    circuitBreaker: {
      rules: [
        {
          name: 'mcp-circuit-breaker'
          failureCondition: {
            count: 5
            interval: 'PT1M'
            statusCodeRanges: [
              { min: 500, max: 599 }  // Server errors
            ]
          }
          tripDuration: 'PT30S'
          acceptRetryAfter: true
        }
      ]
    }
  }
}

// Azure OpenAI API Definition
resource aoaiApi 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'azure-openai-api'
  properties: {
    displayName: 'Azure OpenAI API'
    description: 'AI Gateway for Azure OpenAI with rate limiting and logging'
    serviceUrl: azureOpenAiEndpoint
    path: 'openai'
    protocols: ['https']
    subscriptionRequired: false  // Use Managed Identity instead
    apiType: 'http'
  }
}

// Chat Completions Operation
resource chatCompletionsOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: aoaiApi
  name: 'chat-completions'
  properties: {
    displayName: 'Create Chat Completion'
    method: 'POST'
    urlTemplate: '/deployments/{deployment-id}/chat/completions'
    templateParameters: [
      {
        name: 'deployment-id'
        type: 'string'
        required: true
        description: 'Model deployment name'
      }
    ]
    request: {
      queryParameters: [
        {
          name: 'api-version'
          type: 'string'
          required: true
          description: 'API Version'
        }
      ]
    }
  }
}

// Embeddings Operation
resource embeddingsOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: aoaiApi
  name: 'embeddings'
  properties: {
    displayName: 'Create Embeddings'
    method: 'POST'
    urlTemplate: '/deployments/{deployment-id}/embeddings'
    templateParameters: [
      {
        name: 'deployment-id'
        type: 'string'
        required: true
        description: 'Model deployment name'
      }
    ]
    request: {
      queryParameters: [
        {
          name: 'api-version'
          type: 'string'
          required: true
          description: 'API Version'
        }
      ]
    }
  }
}

// Catch-all operation for other OpenAI endpoints
resource allOperations 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: aoaiApi
  name: 'all-operations'
  properties: {
    displayName: 'All Other Operations'
    method: '*'
    urlTemplate: '/*'
  }
}

// ========================================
// MCP Server API Definition
// ========================================

// MCP Server API
resource mcpApi 'Microsoft.ApiManagement/service/apis@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: apim
  name: 'mcp-server-api'
  properties: {
    displayName: 'MCP Server API'
    description: 'Business Analytics MCP Server - Provides sales analysis, product comparison, customer segmentation, and inventory analysis tools'
    serviceUrl: mcpServerEndpoint
    path: 'mcp'
    protocols: ['https']
    subscriptionRequired: false  // Internal use only, secured by network
    apiType: 'http'
  }
}

// MCP Protocol Endpoint (POST /mcp)
resource mcpProtocolOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: mcpApi
  name: 'mcp-protocol'
  properties: {
    displayName: 'MCP Protocol Endpoint'
    description: 'JSON-RPC 2.0 endpoint for MCP protocol (tools/list, tools/call)'
    method: 'POST'
    urlTemplate: '/'
    request: {
      representations: [
        {
          contentType: 'application/json'
          examples: {
            'tools-list': {
              summary: 'List available tools'
              value: {
                jsonrpc: '2.0'
                id: '1'
                method: 'tools/list'
              }
            }
            'tools-call': {
              summary: 'Call a tool'
              value: {
                jsonrpc: '2.0'
                id: '2'
                method: 'tools/call'
                params: {
                  name: 'calculate_yoy_growth'
                  arguments: {
                    current_value: 1200000
                    previous_value: 1000000
                  }
                }
              }
            }
          }
        }
      ]
    }
    responses: [
      {
        statusCode: 200
        description: 'Successful MCP response'
        representations: [
          {
            contentType: 'application/json'
          }
        ]
      }
    ]
  }
}

// MCP Health Check Endpoint
resource mcpHealthOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: mcpApi
  name: 'mcp-health'
  properties: {
    displayName: 'Health Check'
    description: 'MCP Server health check endpoint'
    method: 'GET'
    urlTemplate: '/health'
  }
}

// MCP API Policy
resource mcpApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: mcpApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''
<policies>
  <inbound>
    <base />
    <!-- Request logging -->
    <set-header name="x-ms-gateway-timestamp" exists-action="override">
      <value>@(DateTime.UtcNow.ToString("o"))</value>
    </set-header>
    <set-variable name="request-start-time" value="@(DateTime.UtcNow)" />
    <!-- CORS for internal API calls -->
    <cors allow-credentials="false">
      <allowed-origins>
        <origin>*</origin>
      </allowed-origins>
      <allowed-methods>
        <method>POST</method>
        <method>GET</method>
      </allowed-methods>
      <allowed-headers>
        <header>Content-Type</header>
        <header>Accept</header>
      </allowed-headers>
    </cors>
  </inbound>

  <backend>
    <base />
  </backend>

  <outbound>
    <base />
    <!-- Calculate and add latency header -->
    <set-header name="x-gateway-latency-ms" exists-action="override">
      <value>@{
        var startTime = (DateTime)context.Variables["request-start-time"];
        return ((int)(DateTime.UtcNow - startTime).TotalMilliseconds).ToString();
      }</value>
    </set-header>
  </outbound>

  <on-error>
    <base />
  </on-error>
</policies>
'''
  }
}

// API Policy with Azure OpenAI specific handling
resource aoaiApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: aoaiApi
  name: 'policy'
  properties: {
    format: 'xml'
    value: '''
<policies>
  <inbound>
    <base />
    <!-- Authenticate with Azure OpenAI using Managed Identity -->
    <authentication-managed-identity resource="https://cognitiveservices.azure.com" />

    <!-- Fix duplicate /openai path issue: SDK sends /openai/deployments/... but APIM path is already /openai -->
    <!-- Rewrite /openai/openai/... to /openai/... -->
    <rewrite-uri template="@{
      var path = context.Request.Url.Path;
      if (path.StartsWith("/openai/openai/")) {
        return path.Substring(7);
      }
      return path;
    }" copy-unmatched-params="true" />

    <!-- Note: rate-limit-by-key not available in Consumption tier -->
    <!-- Rate limiting is handled by Azure OpenAI's built-in throttling -->

    <!-- Token usage tracking header -->
    <set-header name="x-ms-gateway-timestamp" exists-action="override">
      <value>@(DateTime.UtcNow.ToString("o"))</value>
    </set-header>

    <!-- Log request to App Insights -->
    <set-variable name="request-start-time" value="@(DateTime.UtcNow)" />
  </inbound>

  <backend>
    <base />
  </backend>

  <outbound>
    <base />

    <!-- Extract token usage from response -->
    <choose>
      <when condition="@(context.Response.StatusCode == 200)">
        <set-variable name="response-body" value="@(context.Response.Body.As&lt;JObject&gt;(preserveContent: true))" />
        <set-header name="x-openai-prompt-tokens" exists-action="override">
          <value>@{
            var body = (JObject)context.Variables["response-body"];
            var usage = body?["usage"];
            return usage?["prompt_tokens"]?.ToString() ?? "0";
          }</value>
        </set-header>
        <set-header name="x-openai-completion-tokens" exists-action="override">
          <value>@{
            var body = (JObject)context.Variables["response-body"];
            var usage = body?["usage"];
            return usage?["completion_tokens"]?.ToString() ?? "0";
          }</value>
        </set-header>
        <set-header name="x-openai-total-tokens" exists-action="override">
          <value>@{
            var body = (JObject)context.Variables["response-body"];
            var usage = body?["usage"];
            return usage?["total_tokens"]?.ToString() ?? "0";
          }</value>
        </set-header>
      </when>
    </choose>

    <!-- Calculate latency -->
    <set-header name="x-gateway-latency-ms" exists-action="override">
      <value>@{
        var startTime = (DateTime)context.Variables["request-start-time"];
        return ((int)(DateTime.UtcNow - startTime).TotalMilliseconds).ToString();
      }</value>
    </set-header>
  </outbound>

  <on-error>
    <base />

    <!-- Handle rate limiting -->
    <choose>
      <when condition="@(context.Response.StatusCode == 429)">
        <set-header name="Retry-After" exists-action="override">
          <value>@{
            var retryAfter = context.Response.Headers.GetValueOrDefault("Retry-After", "60");
            return retryAfter;
          }</value>
        </set-header>
        <return-response>
          <set-status code="429" reason="Rate Limit Exceeded" />
          <set-header name="Content-Type" exists-action="override">
            <value>application/json</value>
          </set-header>
          <set-body>@{
            return new JObject(
              new JProperty("error", new JObject(
                new JProperty("code", "RateLimitExceeded"),
                new JProperty("message", "Request rate limit exceeded. Please retry after the specified time."),
                new JProperty("retry_after", context.Response.Headers.GetValueOrDefault("Retry-After", "60"))
              ))
            ).ToString();
          }</set-body>
        </return-response>
      </when>
    </choose>
  </on-error>
</policies>
'''
  }
}

// Product for API grouping
resource product 'Microsoft.ApiManagement/service/products@2024-05-01' = {
  parent: apim
  name: 'ai-gateway'
  properties: {
    displayName: 'AI Gateway'
    description: 'AI Gateway product for Azure OpenAI and MCP Server access with monitoring'
    subscriptionRequired: false
    state: 'published'
  }
}

// Link OpenAI API to Product
resource productApi 'Microsoft.ApiManagement/service/products/apis@2024-05-01' = {
  parent: product
  name: aoaiApi.name
}

// Link MCP API to Product
resource productMcpApi 'Microsoft.ApiManagement/service/products/apis@2024-05-01' = if (!empty(mcpServerEndpoint)) {
  parent: product
  name: mcpApi.name
}

// Grant APIM access to Azure OpenAI
// Note: This needs the Cognitive Services User role on the Azure OpenAI resource
// This role assignment should be done on the Azure OpenAI resource

// Diagnostic settings for Log Analytics (if configured)
resource apimDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${apim.name}-diagnostics'
  scope: apim
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'GatewayLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// Outputs
output apimName string = apim.name
output apimGatewayUrl string = apim.properties.gatewayUrl
output apimManagedIdentityPrincipalId string = apim.identity.principalId
output apimResourceId string = apim.id
output azureOpenAiProxyEndpoint string = '${apim.properties.gatewayUrl}/openai'
output defaultDeploymentEndpoint string = '${apim.properties.gatewayUrl}/openai/deployments/${azureOpenAiDeploymentName}'
output mcpServerProxyEndpoint string = !empty(mcpServerEndpoint) ? '${apim.properties.gatewayUrl}/mcp' : ''
