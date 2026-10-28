# Higgsfield AI — Complete OpenCode Setup Summary

**Status**: ✅ MCP Config Done | ✅ Skills Installed | 🔄 CLI Auth Pending | 🔄 Python SDK Installing

---

## What's Been Set Up

### 1. ✅ OpenCode MCP Config (`~/.config/opencode/opencode.json`)
Added Higgsfield MCP server with Bearer token file auth:

```json
"higgsfield": {
  "type": "remote",
  "url": "https://mcp.higgsfield.ai/mcp",
  "enabled": true,
  "headers": {
    "Authorization": "Bearer {file:./higgsfield.token}"
  },
  "oauth": false
}
```

**Note**: Uses `{file:./higgsfield.token}` workaround because OpenCode's OAuth sends `openid` scope which Clerk rejects. Token must be placed at `~/.config/opencode/higgsfield.token`.

### 2. ✅ Higgsfield CLI + 9 Skills Installed
```bash
npm i -g @higgsfield/cli          # v1.2.2 installed
npx skills add higgsfield-ai/skills  # 9 skills added
```

**Available Slash Commands** (in Claude Code, Cursor, Codex, GitHub Copilot):
| Skill | Slash Command | Purpose |
|-------|---------------|---------|
| Generate | `/higgsfield:higgsfield-generate` | Universal: images, video, 3D, audio (30+ models) |
| Soul ID | `/higgsfield:higgsfield-soul-id` | Train face identity → reuse across generations |
| Product Photoshoot | `/higgsfield:higgsfield-product-photoshoot` | 10 modes: studio, lifestyle, hero, carousel, ad, virtual try-on |
| Brand Kit | `/higgsfield:higgsfield-brandkit` | Palettes, SVG logos, typography, mockups, brandbooks (PPTX/PDF) |
| Marketplace Cards | `/higgsfield:higgsfield-marketplace-cards` | Compliant product cards + A+ modules |
| Websites | `/higgsfield:higgsfield-websites` | React 19 + TanStack Start on Cloudflare Workers |
| Video Explainer | `/higgsfield:higgsfield-video-explainer` | Narrated explainers with Seed Audio + Gemini |
| YouTube Thumbnail | `/higgsfield:higgsfield-youtube-thumbnail` | High-CTR thumbnails with identity preservation |
| Faceless Video | `/higgsfield:higgsfield-faceless-video` | Documentaries, stories, children's music videos |

### 3. 🔄 CLI Authentication (Pending)
**Action Required**: The `higgsfield auth login` command opened a browser window. Complete the OAuth login there, then run:
```bash
higgsfield workspace set <workspace_id>  # Select your workspace
higgsfield model list                     # Verify auth works
```

### 4. 🔄 Python SDK (`pip install higgsfield-client`)
Installing in background. After completion:
```bash
export HF_KEY="your-key-id:your-key-secret"  # From console.higgsfield.ai
python -c "import higgsfield_client; print('OK')"
```

### 5. 📁 Created Files

| File | Purpose |
|------|---------|
| `~/.config/opencode/opencode.json` | MCP config with higgsfield entry |
| `~/.config/opencode/higgsfield.token` | **Create after auth** - Bearer token for MCP |
| `scripts/higgsfield-token-helper.ps1` | Extract token from browser/Claude Code |
| `scripts/setup-higgsfield-cli.ps1` | One-shot CLI + skills installer |
| `.env.higgsfield.example` | Template for API keys (Python/Node SDKs) |
| `docs/HIGGSFIELD_SETUP_PLAN.md` | This setup plan |

---

## Next Steps (Complete These)

### Step 1: Complete CLI Auth
1. Browser window opened by `higgsfield auth login` → sign in
2. Run: `higgsfield workspace set <your-workspace-id>`
3. Verify: `higgsfield model list` (should show 40+ models)

### Step 2: Get MCP Bearer Token
After CLI auth works, get the token for OpenCode MCP:

**Option A: From Browser DevTools**
1. Open https://mcp.higgsfield.ai/mcp
2. F12 → Network → Refresh
3. Find request to `mcp.higgsfield.ai/mcp`
4. Copy `Authorization: Bearer <token>` header
5. Run: `powershell -ExecutionPolicy Bypass -File scripts/higgsfield-token-helper.ps1 -Source manual -Token "<token>"`

**Option B: From Claude Code** (if you use it)
```bash
# If using Claude Code with Higgsfield MCP connected
powershell -ExecutionPolicy Bypass -File scripts/higgsfield-token-helper.ps1 -Source claude-code
```

### Step 3: Restart OpenCode
```bash
# Close and reopen OpenCode to pick up new MCP config
# Check: OpenCode should show higgsfield tools in MCP list
```

### Step 4: Get API Keys (Optional - for Python/Node SDKs)
1. Go to https://open.higgsfield.ai (separate from website account)
2. Add payment method ($5 min), create API key
3. Copy to `.env.higgsfield` (from `.env.higgsfield.example`)
4. **Note**: API = pay-as-you-go USD (separate billing from website credits)

---

## Usage Examples

### Via Skills (Coding Agents)
```
/higgsfield:higgsfield-generate "cinematic product video, 4K, 10 seconds, studio lighting"
/higgsfield:higgsfield-soul-id "train my face from these 5 photos"
/higgsfield:higgsfield-product-photoshoot "studio hero banner for skincare product"
/higgsfield:higgsfield-brandkit "complete brand identity for tech startup"
```

### Via CLI (Terminal)
```bash
# List models & workflows
higgsfield model list
higgsfield workflow list

# Generate with cost estimate
higgsfield generate cost seedance/v2.5/text-to-video --prompt "..." --duration 10
higgsfield generate create seedance/v2.5/text-to-video --prompt "..." --duration 10 --wait

# Train Soul ID
higgsfield soul-id create --name "my-face" --soul-2 --image ./me1.jpg --image ./me2.jpg --image ./me3.jpg
higgsfield soul-id wait <soul_id>
```

### Via Python SDK (Production Apps)
```python
import higgsfield_client
import os
os.environ["HF_KEY"] = "key_id:key_secret"

# Fire-and-forget with auto-polling
result = higgsfield_client.subscribe(
    "kling/v3.0/text-to-video",
    arguments={"prompt": "Cinematic mountains at sunrise", "duration": 10, "resolution": "720p"}
)
print(result["videos"][0]["url"])
```

### Via Node.js/TypeScript SDK
```typescript
import { higgsfield, config } from "@higgsfield/client/v2";
config({ credentials: process.env.HF_CREDENTIALS });

const result = await higgsfield.subscribe(
  "flux-pro/kontext/max/text-to-image",
  { input: { aspect_ratio: "9:16", prompt: "Sunset" }, withPolling: true }
);
```

### Via MCP (Any MCP Client)
OpenCode will auto-connect on restart. Tools available via `tools/list`.

---

## Important Notes

| Topic | Detail |
|-------|--------|
| **Two Billing Systems** | Website (credits + subscription) ≠ API (USD prepaid) — **no shared billing** |
| **MCP/CLI Uses** | Website plan credits (Free/Starter/Plus/Ultra/Team/Scale) |
| **API Uses** | Prepaid USD balance from open.higgsfield.ai |
| **Output Retention** | URLs valid **7 days only** — download immediately |
| **Rate Limits** | Concurrency: 2 (new) → 10 ($25+) → 20 ($100+) → 40 ($1000+) |
| **Queue Full** | Returns `400` (not `429`) with "Maximum concurrent requests reached" |
| **Open Source?** | **No** — only 2023 LLM training framework is OSS; video models proprietary |

---

## Verification Checklist

- [ ] `opencode.json` has higgsfield MCP entry ✅
- [ ] `npm i -g @higgsfield/cli` installed ✅
- [ ] `npx skills add higgsfield-ai/skills` installed 9 skills ✅
- [ ] `higgsfield auth login` completed in browser ⏳
- [ ] `higgsfield workspace set <id>` run ⏳
- [ ] `higgsfield model list` shows 40+ models ⏳
- [ ] Bearer token extracted to `~/.config/opencode/higgsfield.token` ⏳
- [ ] OpenCode restarted, higgsfield tools visible ⏳
- [ ] Python SDK `pip install higgsfield-client` completed ⏳
- [ ] API keys created at console.higgsfield.ai (optional) ⏳
- [ ] `.env.higgsfield` created from template (optional) ⏳

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP tools not showing in OpenCode | Restart OpenCode; check `higgsfield.token` exists and is valid JWT |
| `No workspace selected` | Run `higgsfield workspace set <id>` after auth |
| OAuth `openid` scope error | Use Bearer token workaround (already configured) |
| Token expired | Re-run `higgsfield-token-helper.ps1` after fresh browser login |
| Skills not showing | Run `npx skills list` — should show all 9 higgsfield-* skills |
| Python SDK import fails | Ensure `pip install higgsfield-client` completed; check `HF_KEY` env var |

---

## Resources

- **Platform**: https://higgsfield.ai/
- **CLI Docs**: https://higgsfield.ai/cli
- **MCP Server**: https://mcp.higgsfield.ai/mcp
- **API Docs**: https://docs.higgsfield.ai/docs
- **API Console**: https://open.higgsfield.ai
- **Skills Repo**: https://github.com/higgsfield-ai/skills
- **MODELS.md**: https://github.com/higgsfield-ai/cli/blob/main/MODELS.md