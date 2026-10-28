# MCP Setup — Complete Summary

## ✅ What's Done

| MCP Server | Status | Config | Notes |
|------------|--------|--------|-------|
| **Higgsfield** | ✅ Configured | `opencode.json` | Remote, Bearer token file auth |
| **Pollinations** | 📝 Documented | Direct API (OpenAI-compatible) | No MCP needed |
| **Other MCPs** | ✅ Preserved | Neon, browser-mcp, chrome-devtools, playwright, desktop-commander, apify, Exa, GitHub | Unchanged |

---

## 📁 Files Created/Updated

| File | Purpose |
|------|---------|
| `~/.config/opencode/opencode.json` | Higgsfield MCP added (Bearer token file auth) |
| `scripts/verify-higgsfield-token.ps1` | Extract/verify Higgsfield Bearer token |
| `scripts/test-pollinations-api.ps1` | Test Pollinations direct API |
| `scripts/test-mcp-higgsfield.ps1` | Test Higgsfield MCP connection |
| `docs/MCP_SETUP_PLAN.md` | Setup plan |
| `docs/CLOUD_VIDEO_GUIDE.md` | Hailuo/Pika + Pollinations API usage |
| `docs/FREE_AI_VIDEO_IMAGE_COMPARISON.md` | Full comparison of 30+ tools |
| `docs/HIGGSFIELD_SETUP_COMPLETE.md` | Higgsfield setup details |

---

## 🔴 Action Required (Manual Steps)

### 1. Complete Higgsfield Auth & Get Token
```bash
# Step 1: Login (opens browser)
higgsfield auth login

# Step 2: Set workspace
higgsfield workspace set <your-workspace-id>

# Step 3: Verify
higgsfield model list

# Step 4: Get Bearer token for OpenCode MCP
# - Open https://mcp.higgsfield.ai/mcp in Chrome
# - F12 → Network → Refresh
# - Find request to mcp.higgsfield.ai/mcp
# - Copy 'Authorization: Bearer <token>' header
# - Save token:
echo "<your-bearer-token>" | Out-File -Encoding UTF8 "$env:USERPROFILE\.config\opencode\higgsfield.token"

# Step 5: Verify token
powershell -ExecutionPolicy Bypass -File scripts\verify-higgsfield-token.ps1
```

### 2. Get Pollinations API Key
```bash
# Go to https://enter.pollinations.ai
# Create/connect a key (secret key: sk_...)
# Set environment variable:
$env:POLLINATIONS_API_KEY = "your-sk-..."
```

### 3. Restart OpenCode
```bash
# Close and reopen OpenCode to load Higgsfield MCP
# Test in OpenCode:
# /higgsfield:higgsfield-generate "test video"
```

---

## 🎯 Ready-to-Use Commands (After Auth)

### Higgsfield (MCP)
```
/higgsfield:higgsfield-generate "cinematic product video, 4K, 10 seconds"
/higgsfield:higgsfield-soul-id "train my face from 5 photos"
/higgsfield:higgsfield-product-photoshoot "studio hero banner for skincare"
/higgsfield:higgsfield-brandkit "complete brand identity for tech startup"
```

### Pollinations (Direct API - OpenAI Compatible)
```python
# Python
from openai import OpenAI
import os
client = OpenAI(base_url="https://gen.pollinations.ai/v1", api_key=os.getenv("POLLINATIONS_API_KEY"))
client.images.generate(model="black-forest-labs/flux.1-schnell", prompt="professional product photo")
```

```javascript
// Node.js
import OpenAI from "openai"
const client = new OpenAI({ baseURL: "https://gen.pollinations.ai/v1", apiKey: process.env.POLLINATIONS_API_KEY })
await client.images.generate({ model: "black-forest-labs/flux.1-schnell", prompt: "..." })
```

### Cloud Video (Web UI)
| Tool | Link | Best For |
|------|------|----------|
| **Hailuo AI** | https://hailuoai.com/video | Highest quality (watermarked) |
| **Pika Labs** | https://pika.art | Commercial use, no watermark |
| **Kling** | https://klingai.com | Daily free credits |

---

## 📋 Verification Checklist

- [ ] `higgsfield auth login` completed
- [ ] `higgsfield workspace set <id>` done
- [ ] `higgsfield model list` shows 40+ models
- [ ] Bearer token saved to `~/.config/opencode/higgsfield.token`
- [ ] `verify-higgsfield-token.ps1` passes
- [ ] Pollinations API key created at enter.pollinations.ai
- [ ] `POLLINATIONS_API_KEY` env var set
- [ ] OpenCode restarted
- [ ] `/higgsfield:higgsfield-generate "test"` works in OpenCode
- [ ] Pollinations API test script passes

---

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| Higgsfield Console | https://higgsfield.ai |
| Higgsfield MCP | https://mcp.higgsfield.ai/mcp |
| Pollinations API | https://gen.pollinations.ai/v1 |
| Pollinations Keys | https://enter.pollinations.ai |
| Hailuo AI Video | https://hailuoai.com/video |
| Pika Labs | https://pika.art |

---

## 💡 Summary for You

**Your setup now has:**
1. **Higgsfield MCP** — for Soul ID, brand consistency, Marketing Studio (uses website credits)
2. **Pollinations Direct API** — unlimited free images/video, commercial OK, OpenAI-compatible
3. **Cloud Video** — Hailuo/Pika for highest quality when needed

**No GPU needed. All free tiers. Commercial use allowed (except Hailuo watermark).**

Complete the 3 manual steps above and you're ready to generate professional videos/images!