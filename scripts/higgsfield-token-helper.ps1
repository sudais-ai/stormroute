<#
.SYNOPSIS
Higgsfield AI MCP Token Helper for OpenCode

.DESCRIPTION
This script helps extract the Higgsfield MCP Bearer token from an existing 
authenticated session (Claude Code, browser, or direct OAuth) and writes it 
to ~/.config/opencode/higgsfield.token for OpenCode to use.

The Higgsfield MCP uses OAuth via Clerk (clerk.higgsfield.ai). OpenCode's 
built-in OAuth flow sends 'openid' scope which Clerk rejects. The workaround 
is to use a Bearer token from an already-authenticated session.

.NOTES
- Token must be refreshed periodically (typically 1 hour for access tokens)
- Run this script after logging into Higgsfield via Claude Code or browser
- The token file is gitignored (never commit tokens)
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Source = "auto",  # auto, claude-code, browser, manual
    
    [Parameter(Mandatory=$false)]
    [string]$TokenFile = "$env:USERPROFILE\.config\opencode\higgsfield.token",
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowToken
)

Write-Host "=== Higgsfield MCP Token Helper ===" -ForegroundColor Cyan
Write-Host "Target token file: $TokenFile" -ForegroundColor Gray

function Get-TokenFromClaudeCode {
    # Try to find token in Claude Code's MCP config or cache
    $claudeConfig = "$env:USERPROFILE\.claude\mcp_config.json"
    $claudeCache = "$env:USERPROFILE\.claude\cache"
    
    if (Test-Path $claudeConfig) {
        $config = Get-Content $claudeConfig -Raw | ConvertFrom-Json
        if ($config.mcpServers.higgsfield -and $config.mcpServers.higgsfield.headers.Authorization) {
            $auth = $config.mcpServers.higgsfield.headers.Authorization
            if ($auth -match 'Bearer\s+(.+)') {
                return $matches[1]
            }
        }
    }
    
    # Check for token files in Claude cache
    $tokenFiles = Get-ChildItem "$env:USERPROFILE\.claude" -Recurse -Filter "*higgsfield*" -File -ErrorAction SilentlyContinue
    foreach ($f in $tokenFiles) {
        $content = Get-Content $f.FullName -Raw
        if ($content -match 'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+') {
            return $matches[0]
        }
    }
    
    return $null
}

function Get-TokenFromBrowser {
    Write-Host "Browser method: You need to extract the token manually." -ForegroundColor Yellow
    Write-Host "1. Open https://mcp.higgsfield.ai/mcp in browser (after OAuth login)" -ForegroundColor Gray
    Write-Host "2. Open DevTools (F12) -> Network tab" -ForegroundColor Gray
    Write-Host "3. Refresh page, find request to mcp.higgsfield.ai/mcp" -ForegroundColor Gray
    Write-Host "4. Copy Authorization header value (Bearer <token>)" -ForegroundColor Gray
    Write-Host "5. Run this script with -Source manual -Token '<token>'" -ForegroundColor Gray
    return $null
}

function Get-TokenManual {
    param([string]$Token)
    if ($Token) { return $Token }
    
    $input = Read-Host "Paste Bearer token (without 'Bearer ' prefix)"
    return $input.Trim()
}

# Main logic
$token = $null

switch ($Source) {
    'auto' {
        Write-Host "Trying auto-detection..." -ForegroundColor Gray
        $token = Get-TokenFromClaudeCode
        if (-not $token) {
            Write-Host "Auto-detection failed. Falling to manual." -ForegroundColor Yellow
            $token = Get-TokenManual
        }
    }
    'claude-code' { $token = Get-TokenFromClaudeCode }
    'browser' { $token = Get-TokenFromBrowser }
    'manual' { 
        param([string]$ManualToken)
        $token = Get-TokenManual -Token $ManualToken
    }
    default { Write-Host "Unknown source: $Source" -ForegroundColor Red; exit 1 }
}

if (-not $token) {
    Write-Host "ERROR: No token obtained" -ForegroundColor Red
    exit 1
}

# Validate JWT format (basic check)
if ($token -notmatch '^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') {
    Write-Host "WARNING: Token doesn't look like a JWT. Proceeding anyway..." -ForegroundColor Yellow
}

# Write token file
$tokenDir = Split-Path $TokenFile -Parent
if (-not (Test-Path $tokenDir)) { New-Item -ItemType Directory -Path $tokenDir -Force | Out-Null }

Set-Content -Path $TokenFile -Value $token -NoNewline -Encoding UTF8
Write-Host "SUCCESS: Token written to $TokenFile" -ForegroundColor Green

if ($ShowToken) {
    Write-Host "Token: $token" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Restart OpenCode to pick up the new MCP config" -ForegroundColor Gray
Write-Host "2. Run 'opencode' and check MCP tools list for higgsfield" -ForegroundColor Gray
Write-Host "3. If token expires, re-run this script" -ForegroundColor Gray