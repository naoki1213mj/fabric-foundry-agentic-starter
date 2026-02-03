<#
.SYNOPSIS
    テストとLintを実行するスクリプト

.DESCRIPTION
    Python API のユニットテストと Ruff Lintを実行します。
    CI/CD と同じチェックをローカルで実行できます。

.PARAMETER LintOnly
    Lintのみ実行

.PARAMETER TestOnly
    テストのみ実行

.PARAMETER Coverage
    カバレッジレポートを生成

.PARAMETER Fix
    Ruff で自動修正可能な問題を修正

.EXAMPLE
    # すべて実行
    .\scripts\test.ps1

    # Lintのみ
    .\scripts\test.ps1 -LintOnly

    # テストのみ（カバレッジ付き）
    .\scripts\test.ps1 -TestOnly -Coverage

    # Lint問題を自動修正
    .\scripts\test.ps1 -LintOnly -Fix
#>

param(
    [switch]$LintOnly,
    [switch]$TestOnly,
    [switch]$Coverage,
    [switch]$Fix
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ApiPath = Join-Path $ProjectRoot "src\api\python"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  テスト・Lint 実行スクリプト" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 仮想環境のチェック
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  仮想環境が有効化されていません" -ForegroundColor Yellow
    Write-Host "   実行: .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host ""
}

# Ruff がインストールされているかチェック
$ruffPath = Get-Command ruff -ErrorAction SilentlyContinue
if (-not $ruffPath) {
    Write-Host "📦 Ruff をインストールしています..." -ForegroundColor Yellow
    uv pip install ruff
}

# pytest がインストールされているかチェック
$pytestPath = Get-Command pytest -ErrorAction SilentlyContinue
if (-not $pytestPath -and -not $LintOnly) {
    Write-Host "📦 pytest をインストールしています..." -ForegroundColor Yellow
    uv pip install -r "$ApiPath\requirements-test.txt"
}

$exitCode = 0

# ============================================
# Lint 実行
# ============================================
if (-not $TestOnly) {
    Write-Host ""
    Write-Host "🔍 Ruff Lint を実行中..." -ForegroundColor Cyan
    Write-Host "─────────────────────────────────────────────" -ForegroundColor Gray

    if ($Fix) {
        Write-Host "   (自動修正モード)" -ForegroundColor Gray
        ruff check $ApiPath --fix
    } else {
        ruff check $ApiPath
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ Lint エラーがあります" -ForegroundColor Red
        Write-Host "   自動修正: .\scripts\test.ps1 -LintOnly -Fix" -ForegroundColor Gray
        $exitCode = 1
    } else {
        Write-Host "✅ Lint OK" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "🎨 フォーマットチェック中..." -ForegroundColor Cyan
    Write-Host "─────────────────────────────────────────────" -ForegroundColor Gray

    if ($Fix) {
        ruff format $ApiPath
        Write-Host "✅ フォーマット適用完了" -ForegroundColor Green
    } else {
        ruff format $ApiPath --check --diff
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "⚠️  フォーマットが必要なファイルがあります" -ForegroundColor Yellow
            Write-Host "   自動修正: .\scripts\test.ps1 -LintOnly -Fix" -ForegroundColor Gray
        } else {
            Write-Host "✅ フォーマット OK" -ForegroundColor Green
        }
    }
}

# ============================================
# テスト実行
# ============================================
if (-not $LintOnly) {
    Write-Host ""
    Write-Host "🧪 ユニットテストを実行中..." -ForegroundColor Cyan
    Write-Host "─────────────────────────────────────────────" -ForegroundColor Gray

    Push-Location $ApiPath
    try {
        if ($Coverage) {
            pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
            Write-Host ""
            Write-Host "📊 カバレッジレポート: $ApiPath\htmlcov\index.html" -ForegroundColor Cyan
        } else {
            pytest tests/ -v
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "❌ テストが失敗しました" -ForegroundColor Red
            $exitCode = 1
        } else {
            Write-Host ""
            Write-Host "✅ すべてのテストがパスしました" -ForegroundColor Green
        }
    }
    finally {
        Pop-Location
    }
}

# ============================================
# 結果サマリー
# ============================================
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  結果サマリー" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "  ✅ すべてのチェックがパスしました！" -ForegroundColor Green
    Write-Host ""
    Write-Host "  次のステップ:" -ForegroundColor Gray
    Write-Host "    git add ." -ForegroundColor Gray
    Write-Host "    git commit -m 'feat: 機能追加'" -ForegroundColor Gray
    Write-Host "    git push" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  ❌ 一部のチェックが失敗しました" -ForegroundColor Red
    Write-Host ""
    Write-Host "  修正後、再度実行してください:" -ForegroundColor Gray
    Write-Host "    .\scripts\test.ps1" -ForegroundColor Gray
    Write-Host ""
}

exit $exitCode
