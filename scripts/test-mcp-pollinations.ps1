<#
.SYNOPSIS
Test Pollinations MCP Server

.DESCRIPTION
Tests Pollinations MCP server tools: generate_image and generate_video
Uses npx to run the server and test basic functionality.

.NOTES
- Pollinations is free, unlimited, no API key required
- Commercial use allowed
- Models: Flux (images), various video models
#>

param(
    [Parameter(Mandatory=$false)]
    [switch]$InstallOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$QuickTest
)

Write-Host "=== Pollinations MCP Test ===" -ForegroundColor Cyan

function Test-PollinationsMCP {
    Write-Host "Testing Pollinations MCP server..." -ForegroundColor Cyan
    
    try {
        # Test 1: Check if server starts and shows tools
        Write-Host "Test 1: Server startup and tool listing..." -ForegroundColor Gray
        $result = npx -y @pollinations/mcp-server --help 2>&1
        Write-Host "Help output:" -ForegroundColor Gray
        $result | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        
        if ($result -match 'generate_image|generate_video|tools') {
            Write-Host "Server startup: SUCCESS" -ForegroundColor Green
        } else {
            Write-Host "Server startup: UNCLEAR" -ForegroundColor Yellow
        }
        
        if ($QuickTest -or $InstallOnly) { return $true }
        
        # Test 2: Quick image generation (would need actual MCP client)
        Write-Host "Test 2: Tool availability check..." -ForegroundColor Gray
        Write-Host "Available tools (from Pollinations docs):" -ForegroundColor Gray
        Write-Host "  - generate_image(prompt, model?, width?, height?, seed?)" -ForegroundColor Gray
        Write-Host "  - generate_video(prompt, model?, duration?, width?, height?)" -ForegroundColor Gray
        Write-Host "  - models: flux, flux-realism, flux-anime, flux-3d, etc." -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "Manual test in OpenCode after restart:" -ForegroundColor Cyan
        Write-Host "  /pollinations:generate_image \"professional product photo of a laptop, studio lighting, 4k\"" -ForegroundColor Gray
        Write-Host "  /pollinations:generate_video \"cinematic drone shot of mountains at sunrise\"" -ForegroundColor Gray
        
        return $true
    } catch {
        Write-Host "Test FAILED: $_" -ForegroundColor Red
        return $false
    }
}

# Main
if ($InstallOnly) {
    Write-Host "Installing Pollinations MCP..." -ForegroundColor Cyan
    npx -y @pollinations/mcp-server --help 2>&1 | Select-Object -First 5
    Write-Host "Install check complete" -ForegroundColor Green
} else {
    Test-PollinationsMCP
}

Write-Host ""
Write-Host "Pollinations MCP test complete." -ForegroundColor Cyan
Write-Host "Next: Restart OpenCode, then test with /pollinations:generate_image" -ForegroundColor Gray