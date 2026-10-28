# Free/Unlimited AI Video & Image Generation — Complete Comparison (2026)

**Goal**: Find tools you can use **freely/unlimited** for video/images, with **MCP server support** for OpenCode/agent integration.

---

## 📊 Quick Decision Matrix

| Your Hardware | Best Free Option | Quality | Setup Difficulty |
|---------------|------------------|---------|------------------|
| **RTX 3060 12GB / 4060 16GB+** | CogVideoX-5B (local) | ⭐⭐⭐⭐ | Medium |
| **RTX 3090/4090 24GB+** | CogVideoX-5B + LTX-Video | ⭐⭐⭐⭐⭐ | Medium |
| **Apple Silicon M1-M4 (32GB+)** | Draw Things MCP / FLUX MCP | ⭐⭐⭐⭐⭐ (images) | Easy |
| **Any (cloud free tiers)** | Runway / Pika / Hailuo / Kling web | ⭐⭐⭐⭐ | Easiest |
| **No GPU / Laptop only** | ComfyUI + AnimateDiff (CPU offload) | ⭐⭐⭐ | Hard |

---

## 🎬 VIDEO GENERATION — Free/Unlimited Options

### 1. CogVideoX (Z.ai) — **BEST LOCAL FREE VIDEO**
| Aspect | Details |
|--------|---------|
| **License** | Apache 2.0 (commercial OK) |
| **Models** | CogVideoX-2B (GTX 1080 Ti), CogVideoX-5B (RTX 3060+), CogVideoX1.5-5B (10s videos), CogVideoX-5B-I2V |
| **VRAM** | 2B: ~6GB | 5B: ~10-12GB | 5B-I2V: ~12GB |
| **Quality** | Good motion, 720p, 5-10s |
| **MCP Servers** | ✅ `kevinten-ai/mcp-video-gen` (supports CogVideoX), `156554395/image-video-generation-mcp` (BigModel) |
| **Local Run** | `pip install cogvideox-factory` (single 4090 fine-tuning) |
| **Cost** | **$0 unlimited** (your electricity) |
| **Commercial** | ✅ Yes |

### 2. Stable Video Diffusion (SVD) — **BEST IMAGE-TO-VIDEO**
| Aspect | Details |
|--------|---------|
| **License** | Custom (research) / ComfyUI nodes MIT |
| **Type** | Image → Video (not text-to-video) |
| **Models** | SVD (14 frames), SVD-XT (25 frames), 1024×576 |
| **VRAM** | ~8-12GB (ComfyUI optimized) |
| **Quality** | Good for animating images, 6 FPS |
| **MCP Servers** | ✅ ComfyUI MCP (`Peleke/comfyui-mcp`, `artokun/comfyui-mcp`) |
| **Cost** | **$0 unlimited** |
| **Commercial** | ⚠️ Check Stability AI license |

### 3. AnimateDiff (via ComfyUI) — **FAST PREVIEWS**
| Aspect | Details |
|--------|---------|
| **License** | MIT (ComfyUI nodes) |
| **Type** | Text-to-video, Image-to-video |
| **Models** | AnimateDiff v3, Lightning 4-step (fast) |
| **VRAM** | ~6-10GB (512×512) |
| **Quality** | Good for short clips, 8-24 FPS |
| **MCP Servers** | ✅ ComfyUI MCP |
| **Cost** | **$0 unlimited** |

### 4. LTX-Video (Lightricks) — **HIGH QUALITY LOCAL**
| Aspect | Details |
|--------|---------|
| **License** | Custom (open weights) |
| **Models** | LTX-2.3, distilled for speed |
| **VRAM** | **24GB+ recommended** (fp8 on 4090), 32GB RAM |
| **Quality** | ⭐⭐⭐⭐⭐ Best open source quality, synchronized audio |
| **MCP Servers** | ✅ ComfyUI MCP (LTX nodes available) |
| **Cost** | **$0 unlimited** (if you have 24GB+ VRAM) |
| **Desktop App** | ✅ `LTX-Desktop` (beta, Windows/Linux/macOS) |

### 5. Pyramid-Flow — **EFFICIENT 10-SEC VIDEOS**
| Aspect | Details |
|--------|---------|
| **License** | Apache 2.0 |
| **Models** | miniFLUX (384p/768p), SD3-based |
| **VRAM** | ~12-16GB (768p 10s) |
| **Quality** | Good 10s at 768p, 24 FPS |
| **MCP Servers** | ❌ None yet (new) |
| **Cost** | **$0 unlimited** |

### 6. Mochi (Genmo) / HunyuanVideo (Tencent) — **TOO HIGH VRAM**
| Model | VRAM Needed | Verdict |
|-------|-------------|---------|
| Mochi 1 | ~60GB single GPU (ComfyUI: ~20GB) | ❌ Consumer no |
| HunyuanVideo | 45-60GB | ❌ Consumer no |

---

## 🖼️ IMAGE GENERATION — Free/Unlimited Options

### 1. FLUX.1 / FLUX.2 (Black Forest Labs) — **BEST QUALITY**
| Aspect | Details |
|--------|---------|
| **Models** | FLUX.1-dev (4-8 min), FLUX.2-dev (30-40 min), FLUX.1-schnell (4 steps!) |
| **VRAM** | 16GB (CPU offload) / 24GB+ (full GPU) |
| **MCP Servers** | ✅ `tehw0lf/flux-mcp` (CUDA/ROCm/MPS), `my13each/Drawthings_MCP` (macOS) |
| **Quality** | ⭐⭐⭐⭐⭐ SOTA open source |
| **Cost** | **$0 unlimited** |

### 2. SDXL / SD3.5 / SD1.5 — **MATURE ECOSYSTEM**
| Aspect | Details |
|--------|---------|
| **Models** | SDXL, SD3.5, SD1.5, 1000s of LoRAs |
| **VRAM** | SD1.5: 4GB | SDXL: 8GB | SD3.5: 12GB+ |
| **MCP Servers** | ✅ **InvokeAI MCP** (`sandraschi/invokeai-mcp`), **ComfyUI MCP** |
| **Features** | ControlNet, IP-Adapter, Inpaint, Outpaint, Upscale |
| **Cost** | **$0 unlimited** |

### 3. InvokeAI — **PROFESSIONAL LOCAL ENGINE**
| Aspect | Details |
|--------|---------|
| **License** | Apache 2.0 |
| **Models** | SD1.5, SDXL, Flux, SD3.5, Qwen Image |
| **VRAM** | 6-12GB depending on model |
| **MCP Server** | ✅ `sandraschi/invokeai-mcp` (full REST bridge) |
| **Features** | 8 gen modes, 76 styles, gallery, workflows, ControlNet, IP-Adapter, 4x upscale |
| **Web UI** | `http://localhost:9090` (dark SOTA app) |

---

## ☁️ FREE TIER CLOUD APIs (Monthly Credits)

| Platform | Free Credits | Video Quality | Duration | API Access | MCP Server |
|----------|--------------|---------------|----------|------------|------------|
| **Runway Gen-3** | 465/month | Good | 5s | Waitlist | ❌ |
| **Pika 1.5** | Limited/month | Good | 3-5s | ✅ pika.art | ❌ |
| **Hailuo (MiniMax)** | Free tier | ⭐⭐⭐⭐⭐ | 6s | ✅ dev.pika.art | ❌ |
| **Kling (可灵)** | 66/day (web) | ⭐⭐⭐⭐ | 5-10s | ❌ Web only | ❌ |
| **Wan (DashScope)** | 50s free (90d) | ⭐⭐⭐⭐ | 5-10s | ✅ SiliconFlow | ✅ `kevinten-ai/mcp-video-gen` |
| **Vidu** | 200 promo | Good | 4s | ✅ | ✅ `kevinten-ai/mcp-video-gen` |
| **SiliconFlow** | $1 signup | 720p | varies | ✅ | ✅ `kevinten-ai/mcp-video-gen` |
| **Google Veo** | GCP credits | ⭐⭐⭐⭐⭐ | 5-8s | ✅ Vertex AI | ✅ `kevinten-ai/mcp-video-gen` |

**Note**: Cloud free tiers are **not unlimited** — monthly caps apply. But good for testing.

---

## 🔌 MCP SERVERS — Complete List

### Local/Unlimited (Run on Your Hardware)

| MCP Server | Type | Supports | Hardware | Install |
|------------|------|----------|----------|---------|
| **`sandraschi/invokeai-mcp`** | Image | SDXL, Flux, SD3.5, ControlNet, IP-Adapter | 6-12GB VRAM | `uv venv + invokeai` |
| **`Peleke/comfyui-mcp`** | Image + Video | SDXL, Flux, SVD, AnimateDiff, LTX | 8-24GB VRAM | ComfyUI + custom nodes |
| **`artokun/comfyui-mcp`** | Image + Video | Same as above + advanced workflows | 8-24GB VRAM | ComfyUI + custom nodes |
| **`tehw0lf/flux-mcp`** | Image | FLUX.1-dev, FLUX.2-dev | 16-24GB VRAM | `pip install flux-mcp` |
| **`my13each/Drawthings_MCP`** | Image | FLUX.1-schnell (4 steps!) | Apple Silicon only | Node.js + Draw Things app |

### Cloud/Provider-Based (Need API Keys)

| MCP Server | Providers | Free Tier | Install |
|------------|-----------|-----------|---------|
| **`kevinten-ai/mcp-video-gen`** | CogVideoX (free!), Wan, Kling, SiliconFlow, Vidu, MiniMax, Veo | CogVideoX = free unlimited local; others = API credits | `npx -y kevinten-ai/mcp-video-gen` |
| **`156554395/image-video-generation-mcp`** | BigModel (CogView, CogVideoX) | CogVideoX-Flash free | `npx -y image-video-generation-mcp` |
| **`Anil-matcha/Wan-3.0-API`** | Wan 3.0 (MuAPI) | 50s free | Python MCP server |

---

## 🏆 RECOMMENDED SETUPS FOR YOU

### Option A: **Local Unlimited (Best Quality, Your Hardware)**
**Requirements**: RTX 3060 12GB+ or 4090 24GB+
```bash
# 1. Install ComfyUI (supports everything)
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI && pip install -r requirements.txt

# 2. Install ComfyUI Manager → add nodes:
# - ComfyUI-Stable-Video-Diffusion (SVD)
# - ComfyUI-AnimateDiff-Evolved
# - ComfyUI-CogVideoXWrapper (for CogVideoX)
# - LTX-Video nodes

# 3. Add ComfyUI MCP to OpenCode
# In opencode.json:
"comfyui": {
  "type": "local",
  "command": ["python", "path/to/comfyui-mcp/main.py"],
  "enabled": true
}
```

### Option B: **CogVideoX via MCP (Easiest Local Video)**
```bash
# 1. Install MCP server
npm i -g kevinten-ai/mcp-video-gen  # or npx -y

# 2. Add to opencode.json:
"cogvideox": {
  "type": "local",
  "command": ["npx", "-y", "kevinten-ai/mcp-video-gen"],
  "enabled": true,
  "env": {
    "COGVIDEO_MODEL": "cogvideox-5b"  # or flash
  }
}
```

### Option C: **Apple Silicon (M1-M4) — Draw Things MCP**
```json
"drawthings": {
  "type": "local",
  "command": ["npx", "-y", "my13each/Drawthings_MCP"],
  "enabled": true
}
```
Uses FLUX.1-schnell (4 steps = fast!) on Apple Silicon.

### Option D: **Hybrid — Local Images + Cloud Video**
```json
// Local images (unlimited)
"flux-mcp": { "type": "local", "command": ["flux-mcp"], "enabled": true },
"invokeai": { "type": "local", "command": ["invokeai-mcp"], "enabled": true },

// Cloud video (free tiers)
"higgsfield": { "type": "remote", "url": "https://mcp.higgsfield.ai/mcp", "enabled": true, "headers": { "Authorization": "Bearer {file:./higgsfield.token}" } }
```

---

## 🚀 QUICK START — What to Do Now

### If you have NVIDIA GPU (12GB+ VRAM):
```bash
# 1. Install ComfyUI + Manager
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI && pip install -r requirements.txt
python -m pip install comfyui-manager

# 2. Install video nodes via Manager:
# - CogVideoXWrapper
# - Stable Video Diffusion
# - AnimateDiff-Evolved

# 3. Add ComfyUI MCP to OpenCode
# (use Peleke/comfyui-mcp or artokun/comfyui-mcp)

# 4. For images: Add flux-mcp or invokeai-mcp
```

### If you have Apple Silicon (M1-M4):
```bash
# 1. Install Draw Things from App Store (free)
# 2. Add DrawThings MCP to OpenCode
# 3. For video: Use cloud free tiers (Hailuo, Runway, Pika)
```

### If you want ZERO hardware requirements:
```bash
# 1. Sign up for free tiers:
# - Runway (465 credits/mo)
# - Hailuo AI (free text-to-video)
# - Pika (free credits)

# 2. Use Higgsfield MCP (already configured) — uses website credits
# 3. For images: Use Pollinations.ai (free API) or cloud free tiers
```

---

## 💡 My Recommendation for You

Given your current setup (Windows, NVIDIA GPU likely), **go with Option A + CogVideoX**:

1. **Images**: `flux-mcp` (local FLUX, unlimited, best quality)
2. **Video**: `kevinten-ai/mcp-video-gen` with CogVideoX provider (free unlimited local)
3. **Keep Higgsfield** for cloud/video features (Soul ID, Marketing Studio, etc.)

This gives you:
- ✅ Unlimited free images (FLUX on your GPU)
- ✅ Unlimited free video (CogVideoX on your GPU)
- ✅ Cloud backup (Higgsfield for advanced features)
- ✅ All via MCP in OpenCode

---

## 📁 Files to Create for Setup

| File | Purpose |
|------|---------|
| `scripts/setup-local-ai.sh` | One-shot ComfyUI + Flux + CogVideoX installer |
| `scripts/comfyui-mcp-config.json` | OpenCode MCP entries for local servers |
| `.env.local-ai.example` | Env vars for local models |
| `docs/LOCAL_AI_SETUP_GUIDE.md` | Detailed hardware-specific guide |

Want me to create the installer scripts and add the MCP configs to your `opencode.json`?