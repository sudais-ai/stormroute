# AI Video/Image Generation Tools — Free & Generous Tier Deep Research
*Compiled: October 2026 | For OpenCode/Agent Integration*

---

## 📊 QUICK REFERENCE: RECOMMENDATION TIERS

| Tier | Meaning |
|------|---------|
| 🏆 **Best Free** | Production-usable free tier, good quality, reasonable limits |
| ✅ **Good Free** | Usable for testing/hobby, some limitations |
| ⚠️ **Limited Free** | Very tight limits, watermarks, or non-commercial only |
| 💰 **Paid Only** | No meaningful free tier |
| ❌ **Avoid** | Deprecated, discontinued, or unusable |

---

## 🎬 OPEN SOURCE VIDEO GENERATION (Self-Hosted, Completely Free)

| Tool | Video? | Image? | Free Limits | Quality | GPU VRAM (Min/Rec) | Commercial Use | License | Setup Complexity | Status | Best For | Agent Integration |
|------|--------|--------|-------------|---------|-------------------|----------------|---------|------------------|--------|----------|-------------------|
| **LTX-Video / LTX-2.5** (Lightricks) | ✅ T2V, I2V, V2V, T2V+Audio | ❌ | Unlimited local | **Excellent** — 4K native, 30-50 FPS, synchronized audio, multishot | 8 GB (distilled) / 24 GB (full) | ✅ Yes (OpenRail-M, free <$10M ARR) | OpenRail-M | Medium (ComfyUI native) | 🟢 **Active** (Jan 2026 v2.5) | **Best overall** — production quality, audio, local control | ComfyUI MCP, CLI |
| **HunyuanVideo-1.5** (Tencent) | ✅ T2V, I2V | ❌ | Unlimited local | **Excellent** — cinematic, 720p native, 129 frames (5.4s), strong prompt adherence | 14 GB (offload) / 24 GB comfortable | ✅ Yes | Apache-ish (Tencent) | Medium (ComfyUI native Nov 2025) | 🟢 **Active** (Nov 2025 v1.5) | **Best cinematic quality** on consumer GPU | ComfyUI MCP, CLI |
| **CogVideoX / CogVideoX1.5** (ZAI) | ✅ T2V, I2V | ❌ | Unlimited local | **Very Good** — 10s (v1.5), 720p, good motion | 12 GB (2B) / 24 GB (5B) | ✅ Yes | Apache 2.0 | Medium (Diffusers, SAT) | 🟢 **Active** (Mar 2025 v1.5) | **Best balance** quality/VRAM, Apache 2.0 | Diffusers API, ComfyUI MCP |
| **Mochi 1** (Genmo) | ✅ T2V | ❌ | Unlimited local | **Very Good** — 480p (HD coming), 5.4s, high fidelity | 12 GB (quantized) / 24-48 GB full | ✅ Yes | Apache 2.0 | High (ComfyUI, SwarmUI) | 🟢 **Active** (Nov 2024) | **Best prompt adherence**, research | ComfyUI MCP, CLI |
| **Pyramid-Flow** (Peking Univ) | ✅ T2V, I2V | ❌ | Unlimited local | **Good** — 10s 768p 24fps, competitive with commercial | 16-24 GB | ✅ Yes (research) | Apache 2.0 | Medium | 🟢 **Active** (ICLR 2025) | **Longer duration** (10s), efficient training | ComfyUI MCP |
| **Open-Sora** (HPCAI) | ✅ T2V, I2V, T2I | ✅ | Unlimited local | **Good** — up to 16s 720p, arbitrary aspect ratios | 24 GB+ | ✅ Yes | Apache 2.0 | High | 🟡 **Maintenance** (v1.2 Jun 2024) | **Research**, Sora replication | Custom scripts |
| **AnimateDiff** (Motion modules) | ✅ (on SDXL/SD1.5) | ✅ (base) | Unlimited local | **Good** — depends on base model + motion module | 8-12 GB (SDXL) | ✅ Yes (module dependent) | Varies (module licenses) | Low (A1111/ComfyUI ext) | 🟢 **Active** (v2.0 2024, AnimateLCM) | **Adding motion** to existing SD workflows | A1111/ComfyUI MCP |
| **Stable Video Diffusion (SVD/SVD-XT)** | ✅ I2V only | ❌ | Unlimited local | **Fair** — 14-25 frames, 576x1024, deprecated API | 8-12 GB | ✅ Yes (Stability AI license) | Stability AI Research | Low (Diffusers) | 🔴 **Deprecated API** (Jul 2025) | **Legacy** I2V only, short clips | Diffusers, ComfyUI MCP |
| **Hotshot-XL** | ✅ GIF (1s, 8fps) | ✅ (SDXL base) | Unlimited local | **Fair** — 1s GIFs, works with any SDXL fine-tune | 8 GB (SDXL) | ✅ Yes (with SDXL) | Apache 2.0 (model) | Low (SDXL + motion layers) | 🟡 **Maintenance** (2023) | **Quick GIFs**, SDXL users | A1111/ComfyUI MCP |
| **Wan 2.1 / 2.2** (Alibaba) | ✅ T2V, I2V | ❌ | Unlimited local | **Excellent** — 5B runs on 8GB, 14B high quality | 8 GB (5B) / 16 GB (14B) | ✅ Yes | Apache 2.0 | Medium (ComfyUI) | 🟢 **Active** (2025) | **Best low-VRAM** high quality | ComfyUI MCP |

---

## 🖼️ OPEN SOURCE IMAGE GENERATION (Self-Hosted)

| Tool | Video? | Image? | Free Limits | Quality | GPU VRAM (Min/Rec) | Commercial Use | License | Setup Complexity | Status | Best For | Agent Integration |
|------|--------|--------|-------------|---------|-------------------|----------------|---------|------------------|--------|----------|-------------------|
| **FLUX.2 [dev/klein]** (BFL) | ❌ | ✅ | Unlimited local | **SOTA** — 4MP native, multi-ref (10 images), text rendering | 16 GB (klein) / 24 GB (dev GGUF Q4) | ⚠️ Dev: Non-commercial only; Klein: Apache 2.0 | FLUX Non-Comm / Apache 2.0 | Medium (ComfyUI, Forge) | 🟢 **Active** (Nov 2025) | **Best overall quality**, photorealism, text | ComfyUI MCP, Forge MCP |
| **FLUX.1 [schnell]** (BFL) | ❌ | ✅ | Unlimited local | **Excellent** — 1-4 steps, fast, good quality | 8-12 GB | ✅ Yes | Apache 2.0 | Low (Diffusers, ComfyUI) | 🟢 **Active** (Aug 2024) | **Fast local generation**, Apache 2.0 | ComfyUI MCP, Diffusers API |
| **FLUX.1 [dev]** (BFL) | ❌ | ✅ | Unlimited local | **Excellent** — better quality than schnell | 12-24 GB | ⚠️ Non-commercial only | FLUX Non-Commercial | Low | 🟢 **Active** | **High quality** non-commercial | ComfyUI MCP |
| **AuraFlow v0.3** (Fal AI) | ❌ | ✅ | Unlimited local | **Very Good** — GenEval 0.703, truly open | 12-16 GB | ✅ Yes | Apache 2.0 | Medium (Diffusers) | 🟢 **Active** (Jul 2024) | **Truly open** SD3 alternative | ComfyUI MCP, Diffusers |
| **Playground v2.5** | ❌ | ✅ | Unlimited local | **Excellent aesthetic** — beats SDXL, DALL-E 3, MJ 5.2 in user studies | 8-12 GB (SDXL arch) | ✅ Yes | Playground Community | Low (Diffusers, A1111) | 🟢 **Active** (Feb 2024) | **Best aesthetic quality**, artistic | ComfyUI MCP, A1111 MCP |
| **SDXL / SD3.5 Large** (Stability) | ❌ | ✅ | Unlimited local | **Good** — massive ecosystem, LoRAs, ControlNet | 8 GB (SDXL) / 16 GB (SD3.5) | ✅ Yes (SDXL) / ⚠️ SD3 restrictions | Stability AI Community | Low (huge ecosystem) | 🟢 **Active** | **Maximum customization**, LoRA ecosystem | A1111/ComfyUI MCP |
| **Juggernaut XL / DreamShaper** (Fine-tunes) | ❌ | ✅ | Unlimited local | **Excellent** — photorealistic (Juggernaut) / artistic (DreamShaper) | 8 GB | ✅ Yes | Varies (mostly permissive) | Very Low (drop-in SDXL) | 🟢 **Active** | **Specialized styles**, drop-in SDXL | A1111/ComfyUI MCP |
| **Qwen-Image / Qwen-Image-Edit** (Alibaba) | ❌ | ✅ | Unlimited local | **Very Good** — multilingual text rendering, commercial | 16 GB | ✅ Yes | Apache 2.0 | Medium | 🟢 **Active** (2025) | **Multilingual text**, commercial | ComfyUI MCP |

---

## ☁️ FREE TIER CLOUD APIs (Generous Credits, Pay-As-You-Go After)

| Provider | Video? | Image? | Free Tier Details | Cost After Free | Quality | Commercial Use (Free) | API/CLI/MCP | Best For | Integration with OpenCode |
|----------|--------|--------|-------------------|-----------------|---------|----------------------|-------------|----------|---------------------------|
| **Pollinations.ai** | ✅ (LTX, Wan, Veo, etc.) | ✅ (Flux, GPT-Image, Seedream, Nano Banana) | **Truly free, no key, no signup** — rate limited ~1 req/15s, watermarked; free account removes watermark, raises limits | Free forever (community funded) | Good (uses top models) | ✅ **Yes** (free tier allows commercial) | **REST API** (no key), **OpenAI-compatible**, **MCP server** | **Zero-friction testing**, hobby, prototypes, agents needing free image gen | `curl` / `fetch` / MCP — easiest integration |
| **Fal.ai** | ✅ (Kling, Hailuo, Veo, Seedance, LTX, Wan) | ✅ (Flux, Ideogram, Recraft, Qwen, Nano Banana) | **Promotional credits on signup** (amount varies), then pay-per-output | Images: ~$0.003-0.15/MP; Video: ~$0.05-0.40/sec | **Excellent** (latest models, 4x faster claim) | ❌ No (free credits = evaluation only) | **REST API**, **OpenAI-compatible**, **Official MCP server** (`get_pricing` tool) | **Production API**, best model variety, video + image | MCP server + Python/JS SDK |
| **Replicate** | ✅ (Wan, Seedance, Kling, SVD, LTX) | ✅ (Flux, Ideogram, GPT-Image, Recraft) | **Try-for-Free collection** — limited runs per model, then pay | Per GPU-sec: T4 $0.000225/s, L40S $0.000975/s, A100 $0.0014/s; or per-output pricing | **Excellent** (50,000+ models, official models program) | ❌ No (free = trial only) | **REST API**, **Python/JS SDK**, **Cog** for custom models | **Model variety**, custom model deployment, prototyping | Python SDK, HTTP API |
| **Hugging Face Inference Providers** | ✅ (via partners) | ✅ (via partners) | **$0.10/month free credits** (spent at partner rates), 1000 req/5min rate limit | Pay partner rates (per GPU-sec) | **Variable** (routes to best provider) | ❌ No (credits = eval) | **OpenAI-compatible** (`router.huggingface.co/v1`), **Inference Endpoints** | **Access many providers** via single key, serverless | OpenAI SDK compatible |
| **KIE.ai** | ✅ (Seedance, Veo, Kling, Grok) | ✅ (GPT-Image, Nano Banana, Flux) | **Free credits on signup**, ~30-70% cheaper than official | Discounted pay-per-output | **Excellent** (top models) | ✅ Check terms | **REST API**, **OpenAI-compatible** | **Cost optimization**, unified multi-model API | OpenAI SDK compatible |
| **Together.ai** | ✅ (Sora 2, Veo 3, Seedance, PixVerse) | ✅ (Flux.2, Imagen, Nano Banana, Ideogram) | **❌ No free tier since Jul 2025** — $5 min purchase required | Serverless per-token/image/video; dedicated GPU/hr | **Excellent** (200+ models, Sora 2, Veo 3) | ❌ N/A | **OpenAI-compatible**, **REST API** | **Latest frontier models** (Sora 2, Veo 3), batch API 50% off | OpenAI SDK compatible |
| **RunPod** | ✅ (via Public Endpoints / self-host) | ✅ (via Public Endpoints / self-host) | **❌ No free tier** — referral gives $5-500 credits (one-time) | Pods: RTX 4090 $0.34/hr, H100 $2.69/hr; Serverless: 4090 $1.10/hr | **Depends on model** (you control) | ✅ Yes (your deployment) | **REST API** (Public Endpoints), **GraphQL**, **SSH/Pod access** | **Cheapest GPU rental**, full control, self-host any model | SSH + CLI, or Public Endpoints API |
| **DeepAI** | ❌ | ✅ | Free tier: limited daily generations, watermarked | Pay-per-image | Fair | ❌ No (free) | REST API | Quick tests | Simple REST |
| **Craiyon** | ❌ | ✅ | Free: unlimited but slow, watermarked, ads | Supporter tiers | Basic | ❌ No (free) | REST API | Memes, quick tests | Simple REST |

---

## 🔌 MCP SERVERS FOR AGENT INTEGRATION

| MCP Server | Video? | Image? | Backend | Free/Local? | Setup | Best For | Install Command |
|------------|--------|--------|---------|-------------|-------|----------|-----------------|
| **Higgsfield** (your stack) | ✅ | ✅ | Higgsfield Cloud (Seedance, Nano Banana, GPT-Image, etc.) | Cloud credits (paid) | `higgsfield mcp install` | **Production quality**, brand consistency, Soul ID | Built into your workflow |
| **ComfyUI MCP** (AndrewAltimit) | ✅ | ✅ | Local ComfyUI (any model/workflow) | **Free (local GPU)** | Docker/container + MCP config | **Full control** — custom workflows, LoRAs, ControlNet, video (AnimateDiff, LTX, Hunyuan, Wan) | `docker run ...` + MCP stdio |
| **image-gen-mcp** (Ichigo3766) | ❌ | ✅ | A1111/Forge WebUI API | **Free (local GPU)** | Node.js + A1111 with `--api` | **Simple SDXL/Flux** via WebUI, low code | `npx image-gen-mcp` |
| **fal.ai MCP** | ✅ | ✅ | Fal.ai cloud | Promotional credits | `npx @fal-ai/mcp-server` | **Fast cloud inference**, 600+ models, pricing tool | Official MCP |
| **Replicate MCP** (community) | ✅ | ✅ | Replicate cloud | Try-for-free limits | Community maintained | **Model variety**, custom Cog models | Community |
| **Pollinations MCP** (community) | ✅ | ✅ | Pollinations cloud | **Free tier** | Community maintained | **Zero-key free generation** | Community |

> **Recommendation for OpenCode agents**: Use **ComfyUI MCP** for local unlimited generation (video + image), **Pollinations MCP** for zero-setup free cloud, **Fal.ai MCP** for production cloud with best models. Higgsfield for brand-consistent commercial work.

---

## 🎥 SPECIALIZED COMMERCIAL TOOLS — FREE TIER COMPARISON

| Tool | Video? | Image? | Free Tier | Watermark? | Commercial (Free)? | Resolution/Duration Limits | Queue Priority | Best For | Verdict |
|------|--------|--------|-----------|------------|-------------------|---------------------------|----------------|----------|---------|
| **Kling AI** (Kuaishou) | ✅ T2V, I2V, V2V | ❌ | **66 credits/day** (expire daily) ~3-6 clips | ✅ Yes | ❌ No | 5-10s, 720p/1080p, Standard/Pro modes | Low | **Testing quality**, Chinese market | ⚠️ **Limited Free** — daily reset, no commercial, watermarked |
| **Minimax / Hailuo AI** | ✅ T2V, I2V, Director Mode | ✅ | **Daily free credits** (~5-10 videos/day), new user promo: 3 H3 trials + 3000 credits | ✅ Yes (free) | ❌ No (free) | 768p max, 6s clips (free), 1080p paid | Lowest | **Best free daily allowance**, physics/cinematic | ✅ **Good Free** — generous daily, good quality |
| **Luma Dream Machine** | ✅ T2V, I2V, Video-to-Video | ✅ (Photon, GPT-Image) | **~30-80 credits/day** (~1 clip/day), no CC required | ✅ Yes | ❌ No (free) | 720p, 5-10s, standard speed | Low | **Motion quality** on reference frames | ⚠️ **Limited Free** — very tight daily credits |
| **Pika Labs (Pika 2.5)** | ✅ T2V, I2V, Pikaffects, Lip-sync | ✅ | **80 credits/month**, 480p only on free | ❌ **No watermark on free!** | ✅ **Yes** (free allows commercial!) | 480p, 5s max (free), 10s+ paid | Standard | **Fast playful clips**, effects, lip-sync, **commercial free** | 🏆 **Best Free** — commercial allowed, no watermark |
| **Runway Gen-3 Alpha / Turbo** | ✅ T2V, I2V, Director Mode | ✅ | **125 one-time credits** (never refresh) ~2-3 clips | ✅ Yes | ❌ No | 720p, 5-10s, Gen-3 Alpha (10 cr/s) / Turbo (5 cr/s) | N/A (one-time) | **Evaluation only** — not a usable free tier | ❌ **Avoid** — one-time credits, not renewable |
| **Sora / Sora 2** (OpenAI) | ✅ | ✅ | **❌ Discontinued** — web/app shut down Apr 2026, API shutdown Sep 2026 | N/A | N/A | N/A | N/A | **Do not use** | ❌ **Avoid** — discontinued |
| **Google Veo 3 / Veo 3.1** | ✅ | ❌ | Via Vertex AI / Fal / Together — no direct free tier | N/A | Paid only | 720p/1080p/4K, 8s+ | Paid | **Enterprise** via partners | 💰 **Paid Only** |
| **Seedance 2.5** (ByteDance) | ✅ | ❌ | Via Fal / Together / Replicate — no direct free tier | N/A | Paid only | 720p/1080p, 5s+ | Paid | **High quality** via APIs | 💰 **Paid Only** |

---

## 🎯 RECOMMENDATIONS BY USE CASE

### 🏆 **Best Overall Free Stack for Agents (OpenCode)**
```
LOCAL (unlimited, commercial, full control):
├── ComfyUI + ComfyUI MCP Server
│   ├── LTX-Video 2.5 (video + audio, 4K, <8GB VRAM distilled)
│   ├── HunyuanVideo-1.5 (cinematic, 14GB VRAM)
│   ├── Wan 2.1 5B (8GB VRAM, great quality)
│   ├── CogVideoX-5B (12GB VRAM, Apache 2.0)
│   ├── FLUX.2 [klein] / FLUX.1 [schnell] (images, Apache 2.0)
│   ├── AuraFlow v0.3 (images, Apache 2.0)
│   └── Playground v2.5 (images, aesthetic)
└── Pollinations MCP (zero-setup cloud fallback, free, commercial)

CLOUD (production, latest models):
├── Fal.ai MCP (best model variety, promotional credits, MCP pricing tool)
├── KIE.ai (discounted unified API)
└── Replicate (model variety, custom Cog models)
```

### 📱 **For Social Media Content (Free, Commercial OK)**
| Priority | Tool | Why |
|----------|------|-----|
| 1 | **Pika Labs Free** | 80 credits/mo, 480p, **no watermark, commercial allowed**, fast, effects |
| 2 | **Pollinations (Flux + LTX/Wan video)** | Unlimited free, commercial, no key |
| 3 | **Hailuo AI Free** | Daily credits, good quality, but watermarked |
| 4 | **Local: LTX-Video / Wan 2.1** | Unlimited, 4K, commercial, your GPU |

### 🎨 **For Portfolio / Artistic Quality (Local)**
| Priority | Tool | Why |
|----------|------|-----|
| 1 | **FLUX.2 [klein] / FLUX.1 [schnell]** | SOTA images, Apache 2.0, text rendering |
| 2 | **Playground v2.5** | Best aesthetic, beats MJ/DALL-E 3 in studies |
| 3 | **AuraFlow v0.3** | Truly open, Apache 2.0, strong prompt adherence |
| 4 | **SDXL + Juggernaut/DreamShaper** | Maximum LoRA/ControlNet ecosystem |

### 🎬 **For Video Production Quality (Local)**
| Priority | Tool | Why |
|----------|------|-----|
| 1 | **LTX-Video 2.5** | 4K native, synchronized audio, multishot, 8GB VRAM (distilled), commercial <$10M |
| 2 | **HunyuanVideo-1.5** | Cinematic, 720p native, 14GB VRAM, commercial |
| 3 | **Wan 2.1 14B** | Best quality, 16GB VRAM, Apache 2.0 |
| 4 | **CogVideoX1.5-5B** | 10s, 720p, Apache 2.0, 24GB VRAM |
| 5 | **Mochi 1** | Best prompt adherence, 10B params, Apache 2.0 |

### 💻 **For Low VRAM (8-12 GB)**
| Tool | Modality | VRAM | Notes |
|------|----------|------|-------|
| **Wan 2.1 5B** | Video | 8 GB | Excellent quality for VRAM |
| **LTX-Video 2.5 distilled** | Video | 8 GB | 4K, audio, fast |
| **FLUX.1 [schnell]** | Image | 8-12 GB | Apache 2.0, 1-4 steps |
| **SDXL / Juggernaut XL** | Image | 8 GB | Huge ecosystem |
| **Playground v2.5** | Image | 8-12 GB | Aesthetic SOTA |
| **AnimateDiff + SDXL** | Video | 8-12 GB | Motion on existing SDXL |

---

## 🔧 AGENT INTEGRATION PATTERNS (OpenCode)

### Pattern 1: Local ComfyUI MCP (Recommended for Video + Image)
```json
// .opencode/mcp/comfyui.json
{
  "mcpServers": {
    "comfyui": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "--gpus=all", 
               "-v", "${HOME}/comfyui/models:/comfyui/models",
               "-v", "${HOME}/comfyui/output:/comfyui/output",
               "aghunti/comfyui-mcp:latest"],
      "env": {}
    }
  }
}
```
**Capabilities**: Any ComfyUI workflow → MCP tool. Video (LTX, Hunyuan, Wan, CogVideoX, AnimateDiff), Image (FLUX, SDXL, AuraFlow, Playground), ControlNet, LoRA, IP-Adapter, upscaling.

### Pattern 2: Pollinations MCP (Zero-Setup Free Cloud)
```json
{
  "mcpServers": {
    "pollinations": {
      "command": "npx",
      "args": ["@pollinations/mcp-server"],
      "env": {}
    }
  }
}
```
**Capabilities**: Free image (Flux, GPT-Image, Seedream, Nano Banana), video (LTX, Wan, Veo), text, audio. No API key, commercial OK on free.

### Pattern 3: Fal.ai MCP (Production Cloud)
```json
{
  "mcpServers": {
    "fal": {
      "command": "npx",
      "args": ["@fal-ai/mcp-server"],
      "env": { "FAL_KEY": "${FAL_API_KEY}" }
    }
  }
}
```
**Capabilities**: 600+ models, `get_pricing` tool, Kling, Hailuo, Veo, Seedance, Flux, Ideogram, Recraft. Pay-per-output.

### Pattern 4: Higgsfield (Your Stack - Brand Consistent)
```bash
higgsfield mcp install
# Uses your Higgsfield credits, Soul ID, brand kits
```
**Capabilities**: Seedance 2.5, Nano Banana Pro, GPT-Image 2.5, Soul Character consistency, Brand Kit application, Marketing Studio ads.

---

## 📋 HARDWARE REQUIREMENTS QUICK REFERENCE

| VRAM | Video Models (Local) | Image Models (Local) |
|------|---------------------|---------------------|
| **8 GB** | Wan 2.1 5B, LTX 2.5 distilled, AnimateDiff+SDXL | FLUX.1 schnell, SDXL, Playground v2.5, AuraFlow |
| **12 GB** | CogVideoX-2B, Mochi 1 (quantized), LTX 2.5 full | FLUX.1 dev (GGUF Q4), FLUX.2 klein |
| **16 GB** | CogVideoX-5B, Wan 2.1 14B | FLUX.2 dev (GGUF Q4), Qwen-Image |
| **24 GB** | HunyuanVideo-1.5, Mochi 1 full, CogVideoX1.5-5B | FLUX.2 dev full, SD3.5 Large |
| **48 GB+** | Mochi 1 multi-GPU, original HunyuanVideo 13B | — |

---

## ⚡ QUICK START COMMANDS

### ComfyUI + MCP (Local Video + Image)
```bash
# 1. Install ComfyUI (Windows)
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt

# 2. Install ComfyUI Manager (for custom nodes)
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager

# 3. Install video nodes
# LTX-Video: ComfyUI Manager → search "ltx-video" → install
# HunyuanVideo: ComfyUI Manager → search "hunyuanvideo" → install  
# Wan: ComfyUI Manager → search "wan" → install
# CogVideoX: ComfyUI Manager → search "cogvideox" → install

# 4. Run ComfyUI with API
python main.py --listen --port 8188 --enable-cors-header

# 5. Run ComfyUI MCP (in separate terminal)
docker run --rm -i --gpus=all \
  -v ~/ComfyUI/models:/comfyui/models \
  -v ~/ComfyUI/output:/comfyui/output \
  aghunti/comfyui-mcp:latest
```

### Pollinations (Zero-Setup)
```bash
# No install needed - direct HTTP
curl "https://image.pollinations.ai/prompt/A%20beautiful%20sunset%20over%20mountains?model=flux&width=1024&height=1024&nologo=true" -o sunset.png

# Video
curl "https://image.pollinations.ai/prompt/A%20cat%20walking%20in%20rain?model=ltx-video&width=512&height=512" -o cat.mp4
```

### Fal.ai MCP
```bash
# 1. Get API key from fal.ai
# 2. Add to MCP config
export FAL_KEY="your_key_here"
npx @fal-ai/mcp-server
```

---

## 📅 CURRENT STATUS SUMMARY (October 2026)

| Category | Winner | Runner Up | Notes |
|----------|--------|-----------|-------|
| **Local Video (Quality)** | LTX-Video 2.5 | HunyuanVideo-1.5 | LTX has audio, 4K, lower VRAM |
| **Local Video (Low VRAM)** | Wan 2.1 5B | LTX 2.5 distilled | 8GB VRAM, Apache 2.0 |
| **Local Image (Quality)** | FLUX.2 klein | Playground v2.5 | FLUX.2 = SOTA, Klein = Apache 2.0 |
| **Local Image (Speed)** | FLUX.1 schnell | SDXL + Turbo | 1-4 steps |
| **Free Cloud Video (Daily)** | Hailuo AI | Kling AI | Hailuo more generous daily |
| **Free Cloud Video (Monthly)** | Pika Labs | Pollinations | Pika: commercial OK, no watermark |
| **Free Cloud Image (Unlimited)** | Pollinations (Flux) | — | No key, no signup, commercial OK |
| **MCP for Agents (Local)** | ComfyUI MCP | — | Full workflow control |
| **MCP for Agents (Cloud)** | Fal.ai MCP | Pollinations MCP | Fal = production, Pollinations = free |
| **Brand Consistency** | Higgsfield (your stack) | — | Soul ID + Brand Kit |

---

## ⚠️ IMPORTANT CAVEATS

1. **SVD API Deprecated** (Jul 2025) — only self-host via Diffusers
2. **Together.ai Free Tier Removed** (Jul 2025) — now $5 minimum
3. **Sora Discontinued** (Apr 2026) — API shutdown Sep 2026
4. **Runway Free = One-Time 125 Credits** — not renewable
5. **Commercial Use on Free Tiers**: Only **Pika Labs** and **Pollinations** explicitly allow commercial use on free tier
6. **License Check**: Always verify model card for commercial terms (FLUX dev = non-commercial, FLUX schnell/klein = Apache 2.0)
7. **China Access**: Fal.ai, Replicate, Kling, Hailuo may need proxy from Pakistan
8. **Payment from Pakistan**: Use Wise/Payoneer/PayPal for cloud credits; local GPU = no payment needed

---

## 🔗 KEY RESOURCES & LINKS

### Repositories
- LTX-Video: https://github.com/Lightricks/ltx-video
- HunyuanVideo: https://github.com/Tencent-Hunyuan/HunyuanVideo
- CogVideo: https://github.com/zai-org/CogVideo
- Mochi: https://github.com/genmoai/mochi
- Pyramid-Flow: https://github.com/jy0205/Pyramid-Flow
- Open-Sora: https://github.com/hpcaitech/Open-Sora
- FLUX: https://github.com/black-forest-labs/flux
- AuraFlow: https://huggingface.co/fal/AuraFlow-v0.3
- Playground v2.5: https://huggingface.co/playgroundai/playground-v2.5-1024px-aesthetic
- Wan: https://github.com/Wan-Video/Wan2.1
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- ComfyUI MCP: https://gist.github.com/AndrewAltimit/f2a21b1a075cc8c9a151483f89e0f11e
- image-gen-mcp (A1111): https://mcpservers.org/servers/Ichigo3766/image-gen-mcp
- Fal.ai MCP: https://fal.ai/mcp
- Pollinations: https://github.com/pollinations/pollinations

### Model Hubs
- Hugging Face: https://huggingface.co/models?library=diffusers&sort=trending
- Civitai (fine-tunes): https://civitai.com/models?types=Video
- Replicate Models: https://replicate.com/explore

### Benchmarks
- VBench: https://vbench.github.io/
- EvalCrafter: https://evalcrafter.github.io/
- GenEval (images): https://gen-eval.github.io/

---

*Research compiled using Exa, websearch, and public documentation. Prices and free tiers change frequently — verify before production use.*