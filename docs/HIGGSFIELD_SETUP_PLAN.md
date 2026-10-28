# Higgsfield AI — OpenCode Setup Plan

**Objective**: Add Higgsfield AI (video/image generation) to OpenCode MCP config + CLI/SDKs, same pattern as Playwright MCP.

---

## Current State (opencode.json)
- Local MCPs: playwright, chrome-devtools, browser-mcp, desktop-commander (all `node` direct paths)
- Remote MCPs: Neon, apify, Exa, GitHub (all Bearer token auth)

---

## Target State

### 1. Higgsfield MCP Server (Remote)
```
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
- **Auth**: Bearer token from file (workaround for OpenCode OAuth `openid` scope bug)
- **Token source**: Export from Claude Code / browser session after OAuth login
- **Credits**: Uses website plan credits (not API balance)

### 2. CLI + Skills (for coding agents)
```bash
npm i -g @higgsfield/cli
higgsfield auth login
npx skills add higgsfield-ai/skills
```
- Adds skills: `/higgsfield:higgsfield-generate`, `/higgsfield:higgsfield-soul-id`, `/higgsfield:higgsfield-product-photoshoot`, etc.
- Uses OAuth (no API key), same account as web

### 3. Python SDK (higgsfield-client)
```bash
pip install higgsfield-client
export HF_KEY="key_id:key_secret"  # from console.higgsfield.ai
```

### 4. Node.js/TypeScript SDK (@higgsfield/client)
```bash
npm install @higgsfield/client
export HF_CREDENTIALS="key_id:key_secret"
```

---

## Implementation Phases

| Phase | Agent | Files to Create/Modify | Done Criteria |
|-------|-------|------------------------|---------------|
| **1. Recon** | scout | Read opencode.json, verify paths | Current config documented |
| **2. Plan** | architect | `docs/HIGGSFIELD_SETUP_PLAN.md` | This plan approved |
| **3a. MCP Config** | coder-new | `opencode.json` (add higgsfield entry) | MCP server appears in OpenCode |
| **3b. Token Helper** | coder-new | `scripts/higgsfield-token-helper.sh` | Token file created/updated |
| **3c. CLI Setup** | coder-new | `scripts/setup-higgsfield-cli.sh` | CLI + skills installed |
| **3d. SDK Env** | coder-new | `.env.higgsfield.example` | Example env file created |
| **4. QA** | reviewer-quality | Verify all 4 integrations work | Each shows tools/models |
| **5. Ship** | git-agent | Commit config + scripts | Clean push |

---

## 3-Line Summary for User
1. **MCP**: Add `https://mcp.higgsfield.ai/mcp` to opencode.json with Bearer token file auth (OAuth workaround)
2. **CLI**: Install `@higgsfield/cli` + skills for `/higgsfield:*` slash commands in coding agents
3. **SDKs**: Python (`higgsfield-client`) + Node (`@higgsfield/client`) with API keys for production apps

---

## Verification Commands
```bash
# MCP: List tools after OpenCode restart
# (check OpenCode MCP tools list shows higgsfield tools)

# CLI
higgsfield model list
higgsfield workflow list

# Python SDK
python -c "import higgsfield_client; print('OK')"

# Node SDK
node -e "const {higgsfield} = require('@higgsfield/client/v2'); console.log('OK')"
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `~/.config/opencode/opencode.json` | Add higgsfield MCP entry |
| `~/.config/opencode/higgsfield.token` | Bearer token (gitignored) |
| `scripts/setup-higgsfield.sh` | One-shot installer for CLI + skills |
| `scripts/higgsfield-token-helper.sh` | Extract token from browser/Claude |
| `.env.higgsfield.example` | Template for API keys |
| `docs/HIGGSFIELD_SETUP_PLAN.md` | This plan |