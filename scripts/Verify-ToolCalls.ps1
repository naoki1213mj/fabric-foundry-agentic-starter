# Verify-ToolCalls.ps1
# マルチツールテストのログ検証スクリプト
#
# 使用方法:
#   .\scripts\Verify-ToolCalls.ps1
#   .\scripts\Verify-ToolCalls.ps1 -Download
#   .\scripts\Verify-ToolCalls.ps1 -LogPath ".debug_logs/api_logs_latest"

param(
    [switch]$Download,
    [string]$LogPath = "",
    [int]$TailLines = 200
)

$ErrorActionPreference = "Stop"

# 定数
$ResourceGroup = "rg-agent-unified-data-acce-eastus-001"
$AppName = "api-daj6dri4yf3k3z"
$DebugLogsDir = ".debug_logs"

# ログディレクトリの確認
if (-not (Test-Path $DebugLogsDir)) {
    New-Item -ItemType Directory -Path $DebugLogsDir -Force | Out-Null
}

# ログのダウンロード
if ($Download) {
    $ts = Get-Date -Format "yyyyMMddHHmmss"
    $zipPath = Join-Path $DebugLogsDir "api_logs_$ts.zip"
    $extractPath = Join-Path $DebugLogsDir "api_logs_$ts"

    Write-Host "`n📥 Downloading logs from Azure..." -ForegroundColor Cyan
    az webapp log download --name $AppName --resource-group $ResourceGroup --log-file $zipPath

    Write-Host "📦 Extracting logs..." -ForegroundColor Cyan
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

    $LogPath = $extractPath
    Write-Host "✅ Logs extracted to: $extractPath" -ForegroundColor Green
}

# ログパスの自動検出
if (-not $LogPath) {
    $latestLog = Get-ChildItem -Path $DebugLogsDir -Directory |
        Where-Object { $_.Name -match "^api_logs_" } |
        Sort-Object CreationTime -Descending |
        Select-Object -First 1

    if ($latestLog) {
        $LogPath = $latestLog.FullName
        Write-Host "`n🔍 Using latest log directory: $LogPath" -ForegroundColor Yellow
    } else {
        Write-Host "❌ No log directory found. Use -Download to fetch logs." -ForegroundColor Red
        exit 1
    }
}

# Dockerログファイルの検索
$dockerLogs = Get-ChildItem -Path "$LogPath/LogFiles" -Filter "*docker.log" -ErrorAction SilentlyContinue

if (-not $dockerLogs) {
    Write-Host "❌ No docker log files found in $LogPath/LogFiles" -ForegroundColor Red
    exit 1
}

Write-Host "`n" + "=" * 60 -ForegroundColor DarkGray
Write-Host "🔍 TOOL CALL VERIFICATION REPORT" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor DarkGray

# ツール呼び出しパターン
$patterns = @{
    "SQL Query"       = @{
        Pattern = "Function name: run_sql_query"
        Success = "Function run_sql_query succeeded"
        Details = "SQL query executed successfully, returned (\d+) rows"
    }
    "Document Search" = @{
        Pattern = "Function name: search_documents"
        Success = "Function search_documents succeeded"
        Details = "Search returned (\d+) documents"
    }
    "Web Search"      = @{
        Pattern = "Function name: search_web"
        Success = "Function search_web succeeded"
        Error   = "Web search timed out"
        Details = "Web search requested: (.+)"
    }
    "MCP Tools"       = @{
        Pattern = "Function name: mcp_"
        Success = "Function mcp_.* succeeded"
        Details = "MCP tool (.+) executed"
    }
}

# ログ内容の読み込み
$logContent = @()
foreach ($log in $dockerLogs) {
    $logContent += Get-Content $log.FullName -Tail $TailLines -ErrorAction SilentlyContinue
}

# 各ツールの検証
foreach ($tool in $patterns.Keys) {
    $config = $patterns[$tool]

    $calls = $logContent | Select-String -Pattern $config.Pattern -AllMatches
    $successes = $logContent | Select-String -Pattern $config.Success -AllMatches
    $errors = @()
    if ($config.Error) {
        $errors = $logContent | Select-String -Pattern $config.Error -AllMatches
    }

    $status = if ($successes.Count -gt 0 -and $errors.Count -eq 0) { "✅" }
              elseif ($errors.Count -gt 0) { "❌" }
              elseif ($calls.Count -gt 0) { "⏳" }
              else { "➖" }

    Write-Host "`n$status $tool" -ForegroundColor $(
        if ($status -eq "✅") { "Green" }
        elseif ($status -eq "❌") { "Red" }
        elseif ($status -eq "⏳") { "Yellow" }
        else { "Gray" }
    )

    Write-Host "   Calls: $($calls.Count) | Success: $($successes.Count) | Errors: $($errors.Count)" -ForegroundColor White

    # 詳細情報の表示
    if ($config.Details -and $calls.Count -gt 0) {
        $details = $logContent | Select-String -Pattern $config.Details -AllMatches
        foreach ($detail in $details | Select-Object -First 3) {
            $match = [regex]::Match($detail.Line, $config.Details)
            if ($match.Success) {
                Write-Host "   └─ $($match.Groups[1].Value)" -ForegroundColor DarkGray
            }
        }
    }

    # エラーの表示
    foreach ($err in $errors | Select-Object -First 2) {
        Write-Host "   └─ ERROR: $($err.Line -replace '.*ERROR:', '' -replace '\s+', ' ')" -ForegroundColor Red
    }
}

# HTTPリクエスト統計
Write-Host "`n" + "-" * 60 -ForegroundColor DarkGray
Write-Host "📊 HTTP REQUEST STATISTICS" -ForegroundColor Cyan

$httpRequests = $logContent | Select-String -Pattern 'HTTP Request:.*"HTTP/(\d+\.\d+) (\d+)' -AllMatches
$statusCodes = @{}

foreach ($req in $httpRequests) {
    $match = [regex]::Match($req.Line, '"HTTP/\d+\.\d+ (\d+)')
    if ($match.Success) {
        $code = $match.Groups[1].Value
        if ($statusCodes.ContainsKey($code)) {
            $statusCodes[$code]++
        } else {
            $statusCodes[$code] = 1
        }
    }
}

foreach ($code in $statusCodes.Keys | Sort-Object) {
    $color = if ($code -match "^2") { "Green" }
             elseif ($code -match "^4") { "Yellow" }
             elseif ($code -match "^5") { "Red" }
             else { "White" }
    Write-Host "   HTTP $code : $($statusCodes[$code]) requests" -ForegroundColor $color
}

# Agent Framework ログ
Write-Host "`n" + "-" * 60 -ForegroundColor DarkGray
Write-Host "🤖 AGENT FRAMEWORK EVENTS" -ForegroundColor Cyan

$agentEvents = $logContent | Select-String -Pattern 'INFO:agent_framework:|INFO:chat:' -AllMatches | Select-Object -Last 10
foreach ($event in $agentEvents) {
    $line = $event.Line -replace '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*', ''
    $line = $line -replace 'INFO:(agent_framework|chat):', ''
    Write-Host "   $line" -ForegroundColor DarkGray
}

Write-Host "`n" + "=" * 60 -ForegroundColor DarkGray
Write-Host "📁 Log Path: $LogPath" -ForegroundColor DarkGray
Write-Host "⏰ Analysis Time: $(Get-Date -Format 'yyyy/MM/dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""
