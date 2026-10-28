<#
.SYNOPSIS
Local AI Video/Image Generation Setup for Windows (NVIDIA GPU)

.DESCRIPTION
Installs ComfyUI with video nodes (CogVideoX, SVD, AnimateDiff, LTX),
FLUX MCP server, and InvokeAI MCP server for unlimited free local generation.

.REQUIREMENTS
- Windows 10/11
- NVIDIA GPU with 12GB+ VRAM (RTX 3060/4060/3090/4090)
- 32GB+ RAM recommended
- 100GB+ free disk space
- Python 3.10-3.11, Git, Node.js

.NOTES
- Run as Administrator for best results
- ComfyUI Manager installs custom nodes via UI
- MCP servers added to opencode.json automatically
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ComfyUIPath = "$env:USERPROFILE\ComfyUI",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonVersion = "3.11",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipComfyUI,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipFluxMCP,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipInvokeAI,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipCogVideoXMCP,
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoConfigOpenCode,
    
    [Parameter(Mandatory=$false)]
    [switch]$VerifyOnly
)

Write-Host "=== Local AI Video/Image Setup ===" -ForegroundColor Cyan
Write-Host "Target GPU: NVIDIA (12GB+ VRAM recommended)" -ForegroundColor Gray

function Check-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Cyan
    
    $checks = @{}
    
    # Python
    try {
        $py = python --version 2>&1
        $checks.Python = $py
        Write-Host "Python: $py" -ForegroundColor Green
    } catch {
        $checks.Python = "MISSING"
        Write-Host "Python: NOT FOUND - Install from python.org" -ForegroundColor Red
    }
    
    # Git
    try {
        $git = git --version 2>&1
        $checks.Git = $git
        Write-Host "Git: $git" -ForegroundColor Green
    } catch {
        $checks.Git = "MISSING"
        Write-Host "Git: NOT FOUND - Install from git-scm.com" -ForegroundColor Red
    }
    
    # Node.js
    try {
        $node = node --version 2>&1
        $npm = npm --version 2>&1
        $checks.Node = "$node / npm $npm"
        Write-Host "Node: $node, npm: $npm" -ForegroundColor Green
    } catch {
        $checks.Node = "MISSING"
        Write-Host "Node.js: NOT FOUND - Install from nodejs.org" -ForegroundColor Red
    }
    
    # NVIDIA GPU
    try {
        $gpu = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1
        $checks.GPU = $gpu
        Write-Host "GPU: $gpu" -ForegroundColor Green
    } catch {
        $checks.GPU = "NOT DETECTED"
        Write-Host "GPU: nvidia-smi not found or no GPU" -ForegroundColor Yellow
    }
    
    # UV (for InvokeAI)
    try {
        $uv = uv --version 2>&1
        $checks.UV = $uv
        Write-Host "UV: $uv" -ForegroundColor Green
    } catch {
        $checks.UV = "MISSING - will install"
        Write-Host "UV: Not found, will install via pip" -ForegroundColor Yellow
    }
    
    return $checks
}

function Install-ComfyUI {
    if ($SkipComfyUI) { Write-Host "Skipping ComfyUI (--SkipComfyUI)" -ForegroundColor Yellow; return $true }
    
    Write-Host "Installing ComfyUI..." -ForegroundColor Cyan
    
    if (-not (Test-Path $ComfyUIPath)) {
        Write-Host "Cloning ComfyUI to $ComfyUIPath..." -ForegroundColor Gray
        git clone https://github.com/comfyanonymous/ComfyUI.git $ComfyUIPath
    } else {
        Write-Host "ComfyUI exists, updating..." -ForegroundColor Gray
        Set-Location $ComfyUIPath
        git pull
    }
    
    Set-Location $ComfyUIPath
    
    Write-Host "Installing Python dependencies..." -ForegroundColor Gray
    pip install -r requirements.txt
    pip install comfyui-manager
    
    Write-Host "ComfyUI base installed. Launch once to initialize..." -ForegroundColor Gray
    Write-Host "Run: python main.py --listen 127.0.0.1 --port 8188" -ForegroundColor Gray
    Write-Host "Then open http://127.0.0.1:8188 and install nodes via Manager:" -ForegroundColor Gray
    Write-Host "  - CogVideoXWrapper" -ForegroundColor Gray
    Write-Host "  - ComfyUI-Stable-Video-Diffusion" -ForegroundColor Gray
    Write-Host "  - ComfyUI-AnimateDiff-Evolved" -ForegroundColor Gray
    Write-Host "  - LTX-Video (if 24GB+ VRAM)" -ForegroundColor Gray
    
    return $true
}

function Install-FluxMCP {
    if ($SkipFluxMCP) { Write-Host "Skipping FLUX MCP (--SkipFluxMCP)" -ForegroundColor Yellow; return $true }
    
    Write-Host "Installing FLUX MCP server..." -ForegroundColor Cyan
    
    # Check if flux-mcp is available via pip
    try {
        pip install flux-mcp
        Write-Host "flux-mcp installed via pip" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "flux-mcp not on PyPI, trying npm..." -ForegroundColor Yellow
    }
    
    try {
        npm install -g @tehw0lf/flux-mcp
        Write-Host "flux-mcp installed via npm" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "Could not install flux-mcp automatically" -ForegroundColor Red
        Write-Host "Manual: pip install flux-mcp OR npm install -g @tehw0lf/flux-mcp" -ForegroundColor Gray
        return $false
    }
}

function Install-InvokeAIMCP {
    if ($SkipInvokeAI) { Write-Host "Skipping InvokeAI MCP (--SkipInvokeAI)" -ForegroundColor Yellow; return $true }
    
    Write-Host "Installing InvokeAI + MCP..." -ForegroundColor Cyan
    
    # Install UV if needed
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "Installing UV..." -ForegroundColor Gray
        pip install uv
    }
    
    $invokePath = "$env:USERPROFILE\InvokeAI"
    if (-not (Test-Path $invokePath)) {
        Write-Host "Installing InvokeAI via launcher..." -ForegroundColor Gray
        # Use official installer
        $installer = "$env:TEMP\invokeai_installer.py"
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/invoke-ai/InvokeAI/main/installer.py" -OutFile $installer
        python $installer --yes --folder $invokePath
    }
    
    # Install MCP wrapper
    $mcpPath = "$env:USERPROFILE\invokeai-mcp"
    if (-not (Test-Path $mcpPath)) {
        Write-Host "Cloning invokeai-mcp..." -ForegroundColor Gray
        git clone https://github.com/sandraschi/invokeai-mcp.git $mcpPath
    }
    
    Set-Location $mcpPath
    pip install -e .
    
    Write-Host "InvokeAI MCP installed. Run InvokeAI first: $invokePath\invokeai-web.bat" -ForegroundColor Gray
    return $true
}

function Install-CogVideoXMCP {
    if ($SkipCogVideoXMCP) { Write-Host "Skipping CogVideoX MCP (--SkipCogVideoXMCP)" -ForegroundColor Yellow; return $true }
    
    Write-Host "Installing CogVideoX MCP (kevinten-ai/mcp-video-gen)..." -ForegroundColor Cyan
    
    try {
        npm install -g kevinten-ai/mcp-video-gen
        Write-Host "CogVideoX MCP installed globally" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "npm install failed, will use npx at runtime" -ForegroundColor Yellow
        return $true  # npx -y works at runtime
    }
}

function Configure-OpenCode {
    if (-not $AutoConfigOpenCode) { Write-Host "Skipping OpenCode config (--AutoConfigOpenCode not set)" -ForegroundColor Yellow; return $true }
    
    Write-Host "Configuring OpenCode MCP servers..." -ForegroundColor Cyan
    
    $configPath = "$env:USERPROFILE\.config\opencode\opencode.json"
    if (-not (Test-Path $configPath)) {
        Write-Host "OpenCode config not found at $configPath" -ForegroundColor Red
        return $false
    }
    
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
    
    # Add MCP servers
    $newServers = @{}
    
    # ComfyUI MCP
    $newServers.comfyui = @{
        type = "local"
        command = @("python", "$ComfyUIPath\comfyui_mcp_server.py")  # Will need to create
        enabled = $true
        timeout = 300000
    }
    
    # FLUX MCP
    $newServers.flux = @{
        type = "local"
        command = @("flux-mcp")
        enabled = $true
        timeout = 600000
    }
    
    # InvokeAI MCP
    $newServers.invokeai = @{
        type = "local"
        command = @("python", "-m", "invokeai_mcp")
        enabled = $true
        timeout = 300000
    }
    
    # CogVideoX MCP
    $newServers.cogvideox = @{
        type = "local"
        command = @("npx", "-y", "kevinten-ai/mcp-video-gen")
        enabled = $true
        env = @{
            COGVIDEO_PROVIDER = "cogvideox"
        }
        timeout = 300000
    }
    
    # Merge with existing
    $config.mcp = $config.mcp + $newServers
    
    # Backup
    Copy-Item $configPath "$configPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
    
    # Write
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    
    Write-Host "OpenCode config updated. Restart OpenCode to load new MCP servers." -ForegroundColor Green
    return $true
}

function Verify-Installation {
    Write-Host "Verifying installation..." -ForegroundColor Cyan
    
    $results = @{}
    
    # ComfyUI
    if (Test-Path "$ComfyUIPath\main.py") {
        $results.ComfyUI = "INSTALLED"
        Write-Host "ComfyUI: INSTALLED at $ComfyUIPath" -ForegroundColor Green
    } else {
        $results.ComfyUI = "MISSING"
        Write-Host "ComfyUI: NOT FOUND" -ForegroundColor Red
    }
    
    # FLUX MCP
    try { flux-mcp --help 2>$null; $results.FluxMCP = "INSTALLED"; Write-Host "FLUX MCP: INSTALLED" -ForegroundColor Green }
    catch { $results.FluxMCP = "MISSING"; Write-Host "FLUX MCP: NOT FOUND" -ForegroundColor Red }
    
    # InvokeAI MCP
    try { python -m invokeai_mcp --help 2>$null; $results.InvokeAIMCP = "INSTALLED"; Write-Host "InvokeAI MCP: INSTALLED" -ForegroundColor Green }
    catch { $results.InvokeAIMCP = "MISSING"; Write-Host "InvokeAI MCP: NOT FOUND" -ForegroundColor Yellow }
    
    # CogVideoX MCP
    try { npx -y kevinten-ai/mcp-video-gen --help 2>$null; $results.CogVideoXMCP = "AVAILABLE"; Write-Host "CogVideoX MCP: AVAILABLE (npx)" -ForegroundColor Green }
    catch { $results.CogVideoXMCP = "MISSING"; Write-Host "CogVideoX MCP: NOT AVAILABLE" -ForegroundColor Yellow }
    
    return $results
}

# Main
if ($VerifyOnly) {
    Verify-Installation
    exit 0
}

$prereqs = Check-Prerequisites

$success = $true
$success = $success -and (Install-ComfyUI)
$success = $success -and (Install-FluxMCP)
$success = $success -and (Install-InvokeAIMCP)
$success = $success -and (Install-CogVideoXMCP)

if ($AutoConfigOpenCode) {
    $success = $success -and (Configure-OpenCode)
}

Write-Host ""
if ($success) {
    Write-Host "=== SETUP COMPLETE ===" -ForegroundColor Green
    Verify-Installation
    
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "1. Launch ComfyUI: python $ComfyUIPath\main.py --listen 127.0.0.1 --port 8188" -ForegroundColor Gray
    Write-Host "2. Open http://127.0.0.1:8188 → Manager → Install video nodes" -ForegroundColor Gray
    Write-Host "3. Launch InvokeAI: $env:USERPROFILE\InvokeAI\invokeai-web.bat" -ForegroundColor Gray
    Write-Host "4. Restart OpenCode to load MCP servers" -ForegroundColor Gray
    Write-Host "5. Test in OpenCode: /comfyui:generate_image, /flux:generate_image, /cogvideox:generate_video" -ForegroundColor Gray
    
} else {
    Write-Host "=== SETUP HAD ISSUES ===" -ForegroundColor Red
    Write-Host "Check errors above. Re-run with specific -Skip* flags if needed." -ForegroundColor Gray
    exit 1
}