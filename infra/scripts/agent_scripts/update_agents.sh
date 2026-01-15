#!/bin/bash
# Agent Update Script - Bash Version
# This script updates Microsoft Foundry agents using azd environment values
set -e

echo "=========================================="
echo "Microsoft Foundry Agent Update Script"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get values from azd environment or arguments
projectEndpoint="${1:-$(azd env get-value AZURE_AI_AGENT_ENDPOINT 2>/dev/null || echo '')}"
solutionName="${2:-$(azd env get-value SOLUTION_NAME 2>/dev/null || echo '')}"
gptModelName="${3:-$(azd env get-value AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME 2>/dev/null || echo '')}"
aiFoundryResourceId="${4:-$(azd env get-value AI_FOUNDRY_RESOURCE_ID 2>/dev/null || echo '')}"
apiAppName="${5:-$(azd env get-value API_APP_NAME 2>/dev/null || echo '')}"
resourceGroup="${6:-$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null || echo '')}"
usecase="${7:-$(azd env get-value USE_CASE 2>/dev/null || echo 'retail')}"

# Validate required parameters
if [ -z "$projectEndpoint" ] || [ -z "$solutionName" ] || [ -z "$gptModelName" ]; then
    echo "❌ Error: Missing required parameters."
    echo "Required: projectEndpoint, solutionName, gptModelName"
    exit 1
fi

echo "Configuration:"
echo "  Endpoint: $projectEndpoint"
echo "  Solution: $solutionName"
echo "  Model: $gptModelName"
echo "  Use Case: $usecase"
echo ""

# Check Azure authentication
echo "Checking Azure authentication..."
if az account show &> /dev/null; then
    echo "✓ Already authenticated with Azure."
else
    echo "Authenticating with Azure CLI..."
    az login --use-device-code
fi

# Check/Assign Azure AI User role if aiFoundryResourceId is provided
if [ -n "$aiFoundryResourceId" ]; then
    echo "Checking Azure AI User role..."
    signed_user_id=$(az ad signed-in-user show --query id -o tsv 2>/dev/null) || signed_user_id=${AZURE_CLIENT_ID}

    role_assignment=$(MSYS_NO_PATHCONV=1 az role assignment list \
        --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
        --scope "$aiFoundryResourceId" \
        --assignee "$signed_user_id" \
        --query "[].roleDefinitionId" -o tsv 2>/dev/null || echo "")

    if [ -z "$role_assignment" ]; then
        echo "Assigning Azure AI User role..."
        MSYS_NO_PATHCONV=1 az role assignment create \
            --assignee "$signed_user_id" \
            --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" \
            --scope "$aiFoundryResourceId" \
            --output none 2>/dev/null || true
        echo "✓ Azure AI User role assigned."
    else
        echo "✓ Azure AI User role already assigned."
    fi
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
python -m pip install --upgrade pip --quiet
python -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# Run the new agent creation script
echo ""
echo "Creating/Updating agents..."
output=$(python "$SCRIPT_DIR/create_agents.py" \
    --ai_project_endpoint="$projectEndpoint" \
    --solution_name="$solutionName" \
    --gpt_model_name="$gptModelName" \
    --usecase="$usecase")

echo "$output"

# Extract agent names from output
chatAgentName=$(echo "$output" | grep "^chatAgentName=" | cut -d'=' -f2)
titleAgentName=$(echo "$output" | grep "^titleAgentName=" | cut -d'=' -f2)

# Update App Service and azd environment if values are set
if [ -n "$chatAgentName" ] && [ -n "$titleAgentName" ]; then
    echo ""
    echo "Updating environment..."

    # Update App Service if apiAppName and resourceGroup are provided
    if [ -n "$apiAppName" ] && [ -n "$resourceGroup" ]; then
        echo "Updating App Service: $apiAppName"
        az webapp config appsettings set \
            --resource-group "$resourceGroup" \
            --name "$apiAppName" \
            --settings AGENT_NAME_CHAT="$chatAgentName" AGENT_NAME_TITLE="$titleAgentName" \
            --output none 2>/dev/null || true
        echo "✓ App Service updated."
    fi

    # Update azd environment
    azd env set AGENT_NAME_CHAT "$chatAgentName" 2>/dev/null || true
    azd env set AGENT_NAME_TITLE "$titleAgentName" 2>/dev/null || true
    echo "✓ azd environment updated."
fi

echo ""
echo "=========================================="
echo "✓ Agent update completed successfully!"
echo "=========================================="
