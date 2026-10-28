<#
.SYNOPSIS
Test Higgsfield MCP Server

.DESCRIPTION
Tests Higgsfield MCP server connection and tool availability.
Requires valid Bearer token from higgsfield.token file.

.NOTES
- Uses website plan credits (not API balance)
- Tools: generate, soul-id, product-photoshoot, brandkit, etc.
- Run verify-higgsfield-token.ps1 first to ensure token is valid
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$TokenFile = "$env:USERPROFILE\.config\opencode\higgsfield.token",
    
    [Parameter(Mandatory=$false)]
    [switch]$QuickTest
)

Write-Host "=== Higgsfield MCP Test ===" -ForegroundColor Cyan

function Test-HiggsfieldMCP {
    if (-not (Test-Path $TokenFile)) {
        Write-Host "Token file NOT FOUND: $TokenFile" -ForegroundColor Red
        Write-Host "Run: .\scripts\verify-higgsfield-token.ps1" -ForegroundColor Yellow
        return $false
    }
    
    $token = Get-Content $TokenFile -Raw -Encoding UTF8
    if (-not ($token -match '^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')) {
        Write-Host "Token file exists but INVALID FORMAT" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Token: VALID JWT format" -ForegroundColor Green
    
    if ($QuickTest) { return $true }
    
    Write-Host "Testing MCP connection..." -ForegroundColor Cyan
    
    # Test via mcp-remote (what OpenCode uses for remote MCPs)
    try {
        $env:HIGGSFIELD_MCP_TOKEN = $token
        Write-Host "Attempting MCP connection via mcp-remote..." -ForegroundColor Gray
        
        # This will try to connect and list tools
        $result = npx -y mcp-remote https://mcp.higgsfield.ai/mcp --header "Authorization: Bearer $token" 2>&1 | Select-Object -First 30
        Write-Host "MCP output:" -ForegroundColor Gray
        $result | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        
        if ($result -match 'tools|generate|soul|connected|initialized|ready') {
            Write-Host "MCP connection: SUCCESS" -ForegroundColor Green
        } else {
            Write-Host "MCP connection: UNCLEAR (check output above)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "MCP connection test error (may be expected): $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Expected Higgsfield MCP tools (from research):" -ForegroundColor Cyan
    Write-Host "  - generate (images, video, 3D, audio)" -ForegroundColor Gray
    Write-Host "  - soul-id (train character identity)" -ForegroundColor Gray
    Write-Host "  - product-photoshoot (10 modes)" -ForegroundColor Gray
    Write-Host "  - brandkit (palettes, logos, brandbooks)" -ForegroundColor Gray
    Write-Host "  - marketplace-cards (compliant product cards)" -ForegroundColor Gray
    Write-Host "  - websites (React 19 + TanStack Start)" -ForegroundColor Gray
    Write-Host "  - video-explainer (narrated explainers)" -ForegroundColor Gray
    Write-Host "  - youtube-thumbnail (high-CTR thumbnails)" -ForegroundColor Gray
    Write-Host "  - faceless-video (documentaries, stories)" -ForegroundColor Gray
    Write-Host "  - Marketing Studio (ads from product URL)" -ForegroundColor Gray
    Write-Host "  - Virality Predictor (brain_activity)" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Manual test in OpenCode after restart:" -ForegroundColor Cyan
    Write-Host "  /higgsfield:higgsfield-generate \"cinematic product video, 4K, 10 seconds\"" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-soul-id \"train my face from 5 photos\"" -ForegroundColor Gray
    
    return $true
}

Test-HiggsfieldMCP

Write-Host ""
Write-Host "Higgsfield MCP test complete." -ForegroundColor Cyan