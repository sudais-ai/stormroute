<#
.SYNOPSIS
Test Pollinations AI via Direct API (OpenAI-Compatible)

.DESCRIPTION
Tests Pollinations AI generation using the OpenAI-compatible API.
No MCP server needed - uses direct HTTP calls.

.NOTES
- Base URL: https://gen.pollinations.ai/v1
- Authentication: Bearer token from enter.pollinations.ai
- Models: Flux (images), various video/audio models
- Free tier: Unlimited with API key
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiKey = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$QuickTest
)

Write-Host "=== Pollinations AI Direct API Test ===" -ForegroundColor Cyan

function Get-ApiKey {
    if ($ApiKey) { return $ApiKey }
    
    # Try to read from environment
    $envKey = $env:POLLINATIONS_API_KEY
    if ($envKey) { return $envKey }
    
    Write-Host "No API key provided." -ForegroundColor Yellow
    Write-Host "Get your key at: https://enter.pollinations.ai" -ForegroundColor Gray
    Write-Host "Set POLLINATIONS_API_KEY environment variable or pass -ApiKey" -ForegroundColor Gray
    return $null
}

function Test-ImageGeneration {
    param([string]$Key)
    
    Write-Host "Testing image generation..." -ForegroundColor Cyan
    
    $url = "https://gen.pollinations.ai/v1/images/generations"
    $body = @{
        model = "black-forest-labs/flux.1-schnell"
        prompt = "professional product photo of a modern laptop, studio lighting, clean white background, 4k"
        n = 1
        size = "1024x1024"
    } | ConvertTo-Json -Depth 3
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Headers @{
            "Authorization" = "Bearer $Key"
            "Content-Type" = "application/json"
        } -Body $body -TimeoutSec 60
        
        if ($response.data -and $response.data[0].url) {
            Write-Host "Image generation: SUCCESS" -ForegroundColor Green
            Write-Host "URL: $($response.data[0].url)" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "Image generation: UNEXPECTED RESPONSE" -ForegroundColor Yellow
            Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
            return $false
        }
    } catch {
        Write-Host "Image generation: FAILED - $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $err = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($err)
            Write-Host "Error: $($reader.ReadToEnd())" -ForegroundColor Red
        }
        return $false
    }
}

function Test-VideoGeneration {
    param([string]$Key)
    
    Write-Host "Testing video generation..." -ForegroundColor Cyan
    
    $url = "https://gen.pollinations.ai/v1/video/generations"
    $body = @{
        model = "minimax/hailuo/video-01"  # or other video model
        prompt = "cinematic drone shot of mountains at sunrise, 4K"
        duration = 5
    } | ConvertTo-Json -Depth 3
    
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Headers @{
            "Authorization" = "Bearer $Key"
            "Content-Type" = "application/json"
        } -Body $body -TimeoutSec 120
        
        if ($response.data -and $response.data[0].url) {
            Write-Host "Video generation: SUCCESS" -ForegroundColor Green
            Write-Host "URL: $($response.data[0].url)" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "Video generation: CHECK RESPONSE" -ForegroundColor Yellow
            Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
            return $false
        }
    } catch {
        Write-Host "Video generation: FAILED - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function List-Models {
    param([string]$Key)
    
    Write-Host "Fetching available models..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "https://gen.pollinations.ai/v1/models" -Method Get -Headers @{
            "Authorization" = "Bearer $Key"
        } -TimeoutSec 30
        
        $models = $response.data | Where-Object { $_.type -in @("image", "video", "audio") }
        Write-Host "Available models:" -ForegroundColor Green
        $models | ForEach-Object { Write-Host "  $($_.id) [$($_.type)] - $($_.publisher)" -ForegroundColor Gray }
        return $true
    } catch {
        Write-Host "Failed to list models: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main
$key = Get-ApiKey
if (-not $key) { exit 1 }

Write-Host "Using API key: $($key.Substring(0, 10))..." -ForegroundColor Gray

List-Models -Key $key

if (-not $QuickTest) {
    Test-ImageGeneration -Key $key
    Test-VideoGeneration -Key $key
}

Write-Host ""
Write-Host "Pollinations API test complete." -ForegroundColor Cyan
Write-Host ""
Write-Host "Usage in OpenCode (via direct API calls):" -ForegroundColor Gray
Write-Host "  # Set env var: `$env:POLLINATIONS_API_KEY = 'your-key'" -ForegroundColor Gray
Write-Host "  # Then use OpenAI SDK with base_url='https://gen.pollinations.ai/v1'" -ForegroundColor Gray