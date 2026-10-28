<#
.SYNOPSIS
Verify Higgsfield MCP Token and Connection

.DESCRIPTION
Checks if the Higgsfield Bearer token file exists and is valid,
then tests MCP connection via npx mcp-remote.

.NOTES
- Requires higgsfield.token at ~/.config/opencode/higgsfield.token
- Token must be extracted from authenticated browser session
- Run after completing: higgsfield auth login
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$TokenFile = "$env:USERPROFILE\.config\opencode\higgsfield.token",
    
    [Parameter(Mandatory=$false)]
    [switch]$TestMCP,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowToken
)

Write-Host "=== Higgsfield MCP Verification ===" -ForegroundColor Cyan

function Check-TokenFile {
    if (Test-Path $TokenFile) {
        $token = Get-Content $TokenFile -Raw -Encoding UTF8
        if ($token -match '^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') {
            Write-Host "Token file: EXISTS (valid JWT format)" -ForegroundColor Green
            if ($ShowToken) { Write-Host "Token: $token" -ForegroundColor Gray }
            return $token
        } else {
            Write-Host "Token file: EXISTS but INVALID FORMAT" -ForegroundColor Red
            return $null
        }
    } else {
        Write-Host "Token file: NOT FOUND at $TokenFile" -ForegroundColor Red
        Write-Host "Run: higgsfield auth login → browser → extract token → save to $TokenFile" -ForegroundColor Yellow
        return $null
    }
}

function Test-MCPConnection {
    param([string]$Token)
    
    Write-Host "Testing MCP connection via mcp-remote..." -ForegroundColor Cyan
    
    $env:HIGGSFIELD_MCP_TOKEN = $Token
    
    try {
        # Test with mcp-remote (used by OpenCode for remote MCPs)
        $result = npx -y mcp-remote https://mcp.higgsfield.ai/mcp --header "Authorization: Bearer $Token" 2>&1 | Select-Object -First 20
        Write-Host "MCP connection test output:" -ForegroundColor Gray
        $result | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        
        if ($result -match 'connected|tools|ready|initialized') {
            Write-Host "MCP connection: SUCCESS" -ForegroundColor Green
            return $true
        } else {
            Write-Host "MCP connection: UNCLEAR (check output)" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "MCP connection: FAILED - $_" -ForegroundColor Red
        return $false
    }
}

function Get-TokenFromBrowser {
    Write-Host "" -ForegroundColor Gray
    Write-Host "To get token from browser:" -ForegroundColor Cyan
    Write-Host "1. Open https://mcp.higgsfield.ai/mcp in Chrome (after higgsfield auth login)" -ForegroundColor Gray
    Write-Host "2. F12 → Network tab → Refresh page" -ForegroundColor Gray
    Write-Host "3. Find request to mcp.higgsfield.ai/mcp" -ForegroundColor Gray
    Write-Host "4. Copy 'Authorization: Bearer <token>' header value" -ForegroundColor Gray
    Write-Host "5. Save token to: $TokenFile" -ForegroundColor Gray
    Write-Host "   (echo <token> | Out-File -Encoding UTF8 $TokenFile)" -ForegroundColor Gray
}

# Main
$token = Check-TokenFile

if ($TestMCP -and $token) {
    Test-MCPConnection -Token $token
}

if (-not $token) {
    Get-TokenFromBrowser
    exit 1
}

Write-Host ""
Write-Host "Verification complete." -ForegroundColor Cyan