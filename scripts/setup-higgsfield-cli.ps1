<#
.SYNOPSIS
Higgsfield AI CLI + Skills One-Shot Installer

.DESCRIPTION
Installs @higgsfield/cli globally and adds higgsfield-ai/skills for 
slash-command integration with coding agents (Claude Code, Cursor, Codex).

.REQUIREMENTS
- Node.js / npm installed
- Higgsfield account (free at https://higgsfield.ai)

.NOTES
- Uses OAuth authentication (no API key needed)
- Skills enable: /higgsfield:higgsfield-generate, /higgsfield:higgsfield-soul-id,
  /higgsfield:higgsfield-product-photoshoot, etc.
- Run this once per machine/user
#>

param(
    [Parameter(Mandatory=$false)]
    [switch]$ForceReinstall,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSkills,
    
    [Parameter(Mandatory=$false)]
    [switch]$VerifyOnly
)

Write-Host "=== Higgsfield CLI + Skills Installer ===" -ForegroundColor Cyan

function Check-Node {
    try {
        $node = node --version
        $npm = npm --version
        Write-Host "Node: $node, npm: $npm" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "ERROR: Node.js/npm not found. Install from https://nodejs.org" -ForegroundColor Red
        return $false
    }
}

function Install-CLI {
    if ($ForceReinstall) {
        Write-Host "Force reinstalling @higgsfield/cli..." -ForegroundColor Yellow
        npm uninstall -g @higgsfield/cli 2>$null
    }
    
    Write-Host "Installing @higgsfield/cli globally..." -ForegroundColor Cyan
    $result = npm install -g @higgsfield/cli 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "CLI installed successfully" -ForegroundColor Green
        return $true
    } else {
        Write-Host "CLI install failed:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        return $false
    }
}

function Auth-CLI {
    Write-Host "Authenticating with Higgsfield (opens browser)..." -ForegroundColor Cyan
    Write-Host "Please complete OAuth login in the browser window." -ForegroundColor Gray
    
    $result = higgsfield auth login 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Authentication successful" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Auth failed or cancelled:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        return $false
    }
}

function Install-Skills {
    if ($SkipSkills) {
        Write-Host "Skipping skills install (--SkipSkills)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "Installing higgsfield-ai/skills..." -ForegroundColor Cyan
    $result = npx skills add higgsfield-ai/skills 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Skills installed successfully" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Skills install failed (may already exist):" -ForegroundColor Yellow
        Write-Host $result -ForegroundColor Yellow
        # Not fatal - skills might already be installed
        return $true
    }
}

function Verify-Install {
    Write-Host "Verifying installation..." -ForegroundColor Cyan
    
    $checks = @{}
    
    # CLI version
    try {
        $ver = higgsfield --version 2>&1
        $checks.CLI = $ver
        Write-Host "CLI: $ver" -ForegroundColor Green
    } catch {
        $checks.CLI = "FAILED"
        Write-Host "CLI: NOT FOUND" -ForegroundColor Red
    }
    
    # Model list (requires auth)
    try {
        $models = higgsfield model list 2>&1
        if ($models -match 'Error|error|unauthorized|login') {
            $checks.Models = "NEEDS AUTH"
            Write-Host "Models: NEEDS AUTH (run 'higgsfield auth login')" -ForegroundColor Yellow
        } else {
            $count = ($models -split "`n" | Where-Object { $_ -match '^\S' }).Count
            $checks.Models = "$count models available"
            Write-Host "Models: $count available" -ForegroundColor Green
        }
    } catch {
        $checks.Models = "FAILED"
        Write-Host "Models: FAILED" -ForegroundColor Red
    }
    
    # Skills
    try {
        $skills = npx skills list 2>&1
        if ($skills -match 'higgsfield') {
            $checks.Skills = "INSTALLED"
            Write-Host "Skills: higgsfield-ai/skills found" -ForegroundColor Green
        } else {
            $checks.Skills = "NOT FOUND"
            Write-Host "Skills: higgsfield-ai/skills NOT found" -ForegroundColor Yellow
        }
    } catch {
        $checks.Skills = "FAILED"
        Write-Host "Skills: FAILED" -ForegroundColor Red
    }
    
    return $checks
}

# Main execution
if (-not (Check-Node)) { exit 1 }

if ($VerifyOnly) {
    Verify-Install
    exit 0
}

$success = $true
$success = $success -and (Install-CLI)
$success = $success -and (Auth-CLI)
$success = $success -and (Install-Skills)

Write-Host ""
if ($success) {
    Write-Host "=== INSTALLATION COMPLETE ===" -ForegroundColor Green
    Verify-Install
    
    Write-Host ""
    Write-Host "Available slash commands (in Claude Code/Cursor/Codex):" -ForegroundColor Cyan
    Write-Host "  /higgsfield:higgsfield-generate      - Universal generation (30+ models)" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-soul-id       - Train character identity" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-product-photoshoot - Product photography (10 modes)" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-brandkit      - Complete brand identity" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-marketplace-cards - Marketplace product cards" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-websites      - Full-stack React apps" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-video-explainer - Narrated explainer videos" -ForegroundColor Gray
    Write-Host "  /higgsfield:higgsfield-youtube-thumbnail - High-impact thumbnails" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "CLI commands:" -ForegroundColor Cyan
    Write-Host "  higgsfield model list                    - List all 40+ models" -ForegroundColor Gray
    Write-Host "  higgsfield workflow list                 - List available workflows" -ForegroundColor Gray
    Write-Host "  higgsfield generate create <model> ...   - Generate with options" -ForegroundColor Gray
    Write-Host "  higgsfield generate cost <model> ...     - Estimate cost before generation" -ForegroundColor Gray
    Write-Host "  higgsfield soul-id create --name X ...   - Train Soul ID" -ForegroundColor Gray
    
} else {
    Write-Host "=== INSTALLATION HAD ISSUES ===" -ForegroundColor Red
    Write-Host "Check errors above. Re-run with -ForceReinstall if needed." -ForegroundColor Gray
    exit 1
}