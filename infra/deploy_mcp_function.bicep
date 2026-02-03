@description('The location for the function app')
param location string

@description('The name of the function app')
param functionAppName string

@description('The name of the app service plan')
param appServicePlanName string

@description('The SKU name for the app service plan')
param appServicePlanSku string = 'B1'

@description('The name of the storage account')
param storageAccountName string

@description('Application Insights name')
param applicationInsightsName string = ''

@description('Managed Identity ID')
param managedIdentityId string = ''

@description('Tags for resources')
param tags object = {}

// Storage Account for Functions
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// App Service Plan (Basic plan for Functions)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: appServicePlanSku
    tier: 'Basic'
    size: 'B1'
    capacity: 1
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: managedIdentityId != '' ? 'UserAssigned' : 'SystemAssigned'
    userAssignedIdentities: managedIdentityId != '' ? {
      '${managedIdentityId}': {}
    } : null
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      pythonVersion: '3.12'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: applicationInsightsName != '' ? reference(resourceId('Microsoft.Insights/components', applicationInsightsName), '2020-02-02').InstrumentationKey : ''
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsName != '' ? reference(resourceId('Microsoft.Insights/components', applicationInsightsName), '2020-02-02').ConnectionString : ''
        }
        {
          name: 'DEMO_MODE'
          value: 'true'
        }
      ]
      cors: {
        allowedOrigins: [
          '*'
        ]
      }
    }
  }
}

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output mcpEndpoint string = 'https://${functionApp.properties.defaultHostName}/api/mcp'
