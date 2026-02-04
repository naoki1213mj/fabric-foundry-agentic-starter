# Agent Update Script - PowerShell Version
# This script updates Microsoft Foundry agents using azd environment values

param(
    [string]$ProjectEndpoint,
    [string]$SolutionName,
    [string]$GptModelName,
    [string]$AiFoundryResourceId,
    [string]$ApiAppName,
    [string]$ResourceGroup,
    [string]$UseCase
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Microsoft Foundry Agent Update Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Get values from azd environment or parameters
function Get-AzdEnvValue {
    param([string]$Key)
    try {
        $value = azd env get-value $Key 2>$null
        return $value
    } catch {
        return $null
    }
}

if (-not $ProjectEndpoint) { $ProjectEndpoint = Get-AzdEnvValue "AZURE_AI_AGENT_ENDPOINT" }
if (-not $SolutionName) { $SolutionName = Get-AzdEnvValue "SOLUTION_NAME" }
if (-not $GptModelName) { $GptModelName = Get-AzdEnvValue "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME" }
if (-not $AiFoundryResourceId) { $AiFoundryResourceId = Get-AzdEnvValue "AI_FOUNDRY_RESOURCE_ID" }
if (-not $ApiAppName) { $ApiAppName = Get-AzdEnvValue "API_APP_NAME" }
if (-not $ResourceGroup) { $ResourceGroup = Get-AzdEnvValue "AZURE_RESOURCE_GROUP" }
if (-not $UseCase) { $UseCase = Get-AzdEnvValue "USE_CASE" }
if (-not $UseCase) { $UseCase = "retail" }

# Validate required parameters
if (-not $ProjectEndpoint -or -not $SolutionName -or -not $GptModelName) {
    Write-Host "❌ Error: Missing required parameters." -ForegroundColor Red
    Write-Host "Required: ProjectEndpoint, SolutionName, GptModelName" -ForegroundColor Yellow
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Endpoint: $ProjectEndpoint"
Write-Host "  Solution: $SolutionName"
Write-Host "  Model: $GptModelName"
Write-Host "  Use Case: $UseCase"
Write-Host ""

# Check Azure authentication
Write-Host "Checking Azure authentication..."
try {
    az account show | Out-Null
    Write-Host "✓ Already authenticated with Azure." -ForegroundColor Green
} catch {
    Write-Host "Authenticating with Azure CLI..."
    az login --use-device-code
}

# Check/Assign Azure AI User role if AiFoundryResourceId is provided
if ($AiFoundryResourceId) {
    Write-Host "Checking Azure AI User role..."
    try {
        $signedUserId = az ad signed-in-user show --query id -o tsv 2>$null
    } catch {
        $signedUserId = $env:AZURE_CLIENT_ID
    }

    $roleAssignment = az role assignment list `
        --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" `
        --scope $AiFoundryResourceId `
        --assignee $signedUserId `
        --query "[].roleDefinitionId" -o tsv 2>$null

    if (-not $roleAssignment) {
        Write-Host "Assigning Azure AI User role..."
        az role assignment create `
            --assignee $signedUserId `
            --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" `
            --scope $AiFoundryResourceId `
            --output none 2>$null
        Write-Host "✓ Azure AI User role assigned." -ForegroundColor Green
    } else {
        Write-Host "✓ Azure AI User role already assigned." -ForegroundColor Green
    }
}

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..."
python -m pip install --upgrade pip --quiet
python -m pip install --quiet -r "$ScriptDir\requirements.txt"

# Run the new agent creation script
Write-Host ""
Write-Host "Creating/Updating agents..."
$output = python "$ScriptDir\create_agents.py" `
    --ai_project_endpoint="$ProjectEndpoint" `
    --solution_name="$SolutionName" `
    --gpt_model_name="$GptModelName" `
    --usecase="$UseCase"

Write-Host $output

# Extract agent names from output (with null safety)
$chatMatch = $output | Select-String "chatAgentName=(.+)"
$titleMatch = $output | Select-String "titleAgentName=(.+)"

$chatAgentName = if ($chatMatch) { $chatMatch.Matches[0].Groups[1].Value.Trim() } else { $null }
$titleAgentName = if ($titleMatch) { $titleMatch.Matches[0].Groups[1].Value.Trim() } else { $null }

# Update App Service and azd environment if values are set
if ($chatAgentName -and $titleAgentName) {
    Write-Host ""
    Write-Host "Updating environment..."

    # Update App Service if ApiAppName and ResourceGroup are provided
    if ($ApiAppName -and $ResourceGroup) {
        Write-Host "Updating App Service: $ApiAppName"
        az webapp config appsettings set `
            --resource-group $ResourceGroup `
            --name $ApiAppName `
            --settings AGENT_NAME_CHAT="$chatAgentName" AGENT_NAME_TITLE="$titleAgentName" `
            --output none 2>$null
        Write-Host "✓ App Service updated." -ForegroundColor Green
    }

    # Update azd environment
    azd env set AGENT_NAME_CHAT $chatAgentName 2>$null
    azd env set AGENT_NAME_TITLE $titleAgentName 2>$null
    Write-Host "✓ azd environment updated." -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✓ Agent update completed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
