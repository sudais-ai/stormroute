# Cloud Video Generation Guide — Hailuo AI & Pika Labs

**For**: High-quality video when local GPU not available  
**Complements**: Pollinations (unlimited free), Higgsfield (brand/Soul ID)

---

## 🎬 Hailuo AI (MiniMax) — Best Free Quality

### Access
- **Web**: https://hailuoai.com/video
- **API**: https://dev.pika.art/models/minimax/h3/text-to-video (paid)

### Free Tier
- **Limit**: ~5-10 videos/day (resets daily)
- **Quality**: ⭐⭐⭐⭐⭐ Best free text-to-video
- **Duration**: 6 seconds
- **Resolution**: 720p
- **Watermark**: Yes (MiniMax branding)
- **Commercial**: No (watermarked)

### Best Practices
1. **Prompts**: Be specific — "cinematic drone shot of snow-capped mountains at golden hour, 4K, smooth camera movement"
2. **Style keywords**: cinematic, photorealistic, 4K, 8K, HDR, volumetric lighting, depth of field
3. **Camera**: drone shot, tracking shot, dolly zoom, aerial view, close-up, wide angle
4. **Lighting**: golden hour, blue hour, studio lighting, natural lighting, rim lighting
5. **Iterate**: Generate 3-4 variations, pick best

### Example Prompts
```
"Product demo: sleek wireless earbuds floating in space, rotating slowly, studio lighting, 4K commercial quality"
"Tech startup office: modern workspace with developers coding, natural light through floor-to-ceiling windows, cinematic"
"App onboarding: smartphone screen showing app UI, finger tapping, smooth transitions, clean background"
```

---

## 🎨 Pika Labs — Commercial OK, No Watermark

### Access
- **Web**: https://pika.art
- **API**: https://pika.art/api (waitlist)

### Free Tier
- **Limit**: 80 credits/month (renews monthly)
- **Quality**: ⭐⭐⭐⭐ Good
- **Duration**: 3-5 seconds
- **Resolution**: 480p (free), 720p/1080p (paid)
- **Watermark**: **No** on free tier ✅
- **Commercial**: **Yes** ✅

### Features
- **Text-to-video**
- **Image-to-video** (upload reference image)
- **Video inpainting** (modify regions)
- **Canvas** (extend video)
- **Lip sync** (audio-driven)

### Best Practices
1. **Start with image-to-video** for more control
2. **Use "Modify Region"** to fix artifacts
3. **Extend duration** with Canvas feature
4. **Combine with Pollinations** for reference images

### Example Workflow
1. Generate reference image in Pollinations: `/pollinations:generate_image "product photo of wireless headphones, clean white background"`
2. Upload to Pika → Image-to-video: "headphones floating, rotating gently, premium commercial lighting"
3. Extend with Canvas if needed
4. Download (no watermark!)

---

## 🔄 RECOMMENDED WORKFLOW

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR VIDEO PIPELINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. REFERENCE IMAGES (Pollinations - FREE, UNLIMITED)      │
│     /pollinations:generate_image "professional product     │
│     photo of [product], studio lighting, 4k, white bg"     │
│                          │                                  │
│                          ▼                                  │
│  2. VIDEO GENERATION (Choose based on need)                │
│                                                             │
│     ┌──────────────────┐   ┌──────────────────┐            │
│     │  HIGHEST QUALITY │   │  COMMERCIAL USE  │            │
│     │  Hailuo AI       │   │  Pika Labs       │            │
│     │  (watermarked)   │   │  (no watermark)  │            │
│     │  ~5-10/day       │   │  80 cred/month   │            │
│     └──────────────────┘   └──────────────────┘            │
│                          │                                  │
│                          ▼                                  │
│  3. POST-PROCESS (Optional)                                │
│     - Upscale: Pollinations / Real-ESRGAN                  │
│     - Edit: CapCut, DaVinci Resolve (free)                 │
│     - Audio: Pollinations generate_audio / ElevenLabs      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 QUICK REFERENCE CARD

| Need | Tool | Access | Cost | Watermark | Commercial |
|------|------|--------|------|-----------|------------|
| **Unlimited images** | Pollinations | MCP/Web | Free | No | ✅ |
| **Unlimited video (low res)** | Pollinations | MCP | Free | No | ✅ |
| **Best quality video** | Hailuo AI | Web | Free tier | Yes | ❌ |
| **Commercial video** | Pika Labs | Web/API | 80 cred/mo | **No** | ✅ |
| **Brand consistency** | Higgsfield | MCP | Website creds | No | ✅ |
| **Character consistency** | Higgsfield Soul ID | MCP | Website creds | No | ✅ |

---

## 🛠️ INTEGRATION WITH OPENCODE

### Pollinations (Direct API - OpenAI Compatible)
```bash
# 1. Get API key at: https://enter.pollinations.ai
# 2. Set environment variable:
$env:POLLINATIONS_API_KEY = "your-key"

# 3. Use via OpenAI SDK in your code:
# Python:
#   from openai import OpenAI
#   client = OpenAI(base_url="https://gen.pollinations.ai/v1", api_key=os.getenv("POLLINATIONS_API_KEY"))
#   client.images.generate(model="black-forest-labs/flux.1-schnell", prompt="...")

# Node.js:
#   import OpenAI from "openai"
#   const client = new OpenAI({ baseURL: "https://gen.pollinations.ai/v1", apiKey: process.env.POLLINATIONS_API_KEY })
#   await client.images.generate({ model: "black-forest-labs/flux.1-schnell", prompt: "..." })

# 4. Direct REST API:
#   curl -X POST "https://gen.pollinations.ai/v1/images/generations" \
#     -H "Authorization: Bearer $POLLINATIONS_API_KEY" \
#     -H "Content-Type: application/json" \
#     -d '{"model": "black-forest-labs/flux.1-schnell", "prompt": "..."}'
```

### Higgsfield (MCP - Already Configured)
```bash
# Brand-consistent video
/higgsfield:higgsfield-generate "marketing studio video for [product URL]"

# Character-consistent video (after Soul ID training)
/higgsfield:higgsfield-soul-id "train my face from 5 photos"
# Then:
/higgsfield:higgsfield-generate "my character using the product, cinematic"
```

### Hailuo / Pika (Web UI - Manual)
1. Open browser → https://hailuoai.com/video or https://pika.art
2. Use reference images from Pollinations
3. Download → use in your projects

---

## 💡 PRO TIPS

1. **Batch reference images**: Generate 10-20 variations in Pollinations, pick best for video input
2. **Consistent style**: Use same prompt structure for all reference images
3. **Aspect ratios**: 
   - Hailuo: 16:9, 9:16, 1:1
   - Pika: 16:9, 9:16, 4:3, 1:1
   - Pollinations: specify in prompt "16:9 aspect ratio"
4. **Loop for social**: Generate 3-5s loops, extend in Pika Canvas
5. **Audio separately**: Use Pollinations `/generate_audio` or ElevenLabs free tier

---

## 🔗 QUICK LINKS

| Tool | Link |
|------|------|
| Hailuo AI Video | https://hailuoai.com/video |
| Pika Labs | https://pika.art |
| Pollinations Web | https://pollinations.ai |
| Higgsfield Console | https://higgsfield.ai |
| Pollinations MCP | `@pollinations/mcp-server` |
| Higgsfield MCP | `https://mcp.higgsfield.ai/mcp` |

---

## 📝 YOUR CURRENT SETUP

| MCP Server | Status | Use For |
|------------|--------|---------|
| **Pollinations** | ✅ Added to opencode.json | Unlimited free images/video |
| **Higgsfield** | ✅ In opencode.json | Soul ID, brand, Marketing Studio |
| **Hailuo/Pika** | Web only | Highest quality video |

**Restart OpenCode** to load Pollinations MCP, then test:
```
/pollinations:generate_image "test image"
/higgsfield:higgsfield-generate "test video"
```