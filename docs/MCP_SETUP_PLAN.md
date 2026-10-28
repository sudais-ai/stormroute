# MCP Setup Plan — Pollinations + Higgsfield + Cloud Video

**Objective**: Add Pollinations MCP (unlimited free images/video), keep Higgsfield MCP (Soul ID, brand), document Hailuo/Pika web UI for high-quality video.

---

## Current State (opencode.json)
- ✅ Higgsfield MCP: Remote, Bearer token file auth, OAuth disabled
- ❌ Pollinations MCP: Not configured
- ✅ Other MCPs: Neon, browser-mcp, chrome-devtools, playwright, desktop-commander, apify, Exa, GitHub

---

## Plan Phases

| Phase | Agent | Files to Create/Modify | Done Criteria |
|-------|-------|------------------------|---------------|
| **1. Recon** | scout | Read opencode.json, verify MCP list | Current state documented ✅ |
| **2. Plan** | architect | `docs/MCP_SETUP_PLAN.md` | This plan approved |
| **3a. Add Pollinations** | coder-new | `opencode.json` (add pollinations entry) | Pollinations MCP appears in OpenCode |
| **3b. Verify Higgsfield** | coder-fix | `scripts/verify-higgsfield-token.ps1` | Token helper works, MCP connects |
| **3c. Cloud Video Doc** | docs-writer | `docs/CLOUD_VIDEO_GUIDE.md` | Hailuo/Pika usage documented |
| **3d. Test Scripts** | tester | `scripts/test-mcp-pollinations.ps1`, `scripts/test-mcp-higgsfield.ps1` | Both test scripts pass |
| **4. QA** | reviewer-quality + browser-qa | Run test scripts, verify in OpenCode | Both MCPs show tools, generate works |
| **5. Fix-loop** | fixer | Fix any issues | All tests green |
| **6. Ship** | git-agent + summarizer | Commit config + docs + scripts | Clean push, final report |

---

## 3-Line Summary for User
1. **Add Pollinations MCP** to opencode.json (local, `npx @pollinations/mcp-server`, no auth needed)
2. **Verify Higgsfield MCP** token helper works, ensure Bearer token is current
3. **Document Hailuo/Pika** web UI usage for high-quality video (no MCP, browser-based)

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `~/.config/opencode/opencode.json` | Add pollinations MCP entry |
| `scripts/verify-higgsfield-token.ps1` | Enhanced token verification |
| `scripts/test-mcp-pollinations.ps1` | Test Pollinations generate_image + generate_video |
| `scripts/test-mcp-higgsfield.ps1` | Test Higgsfield tools list |
| `docs/CLOUD_VIDEO_GUIDE.md` | Hailuo/Pika web UI usage guide |
| `docs/MCP_SETUP_PLAN.md` | This plan |

---

## Verification Commands
```powershell
# Test Pollinations
npx -y @pollinations/mcp-server --help
# In OpenCode: /pollinations:generate_image "test prompt"

# Test Higgsfield
# In OpenCode: /higgsfield:tools/list

# Cloud video - manual browser test
# Hailuo: https://hailuoai.com/video
# Pika: https://pika.art
```