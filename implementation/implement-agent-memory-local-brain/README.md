# Local Brain — Persistent Agent Memory for the AI-Powered SDLC

## Introduction

Local Brain is a CLI + MCP server pattern that gives your AI coding agents **persistent, queryable, semantically-searchable memory** across sessions — backed entirely by SQLite on your own machine. No vector database to provision, no service to deploy, no auth to wire up.

When an agent (Kiro CLI / Kiro IDE, Claude Code, Cursor, or any MCP-compatible client) writes a memory, Local Brain stores it in a per-namespace SQLite file with both an FTS5 full-text index and a `sqlite-vec` semantic index. Reads are direct SQL — milliseconds, offline-capable, no daemon. Embeddings default to a local `sentence-transformers` model (offline, free) but can optionally use **Amazon Bedrock Titan Embeddings v2** when you want managed inference.

This repository is the public reference implementation extracted from a production internal deployment.

#### 🎯 What this pattern solves

AI coding agents are stateless between sessions. Every time you open a new chat, the agent has forgotten:

- The architectural decisions you made yesterday
- The file conventions it learned from your codebase
- The user preferences it inferred ("don't add unsolicited tests", "use my company's style guide")
- The cross-project insights it built up over weeks of work

Most teams reach for a hosted vector DB (OpenSearch, Pinecone, Weaviate) or shove everything into a single context file. Both approaches break: hosted vector DBs add cost, latency, and an auth surface for what is fundamentally a *personal* knowledge store; flat context files don't scale past a few hundred entries and have no semantic recall.

**Local Brain inverts the model.** Memory is per-user, on-disk, namespaced, queryable from any agent runtime, and the only thing that needs to be online is the embedding step (and even that is local by default).

## Solution Architecture

### How it works
1. **Save** — your agent (or shell script, or cron job) writes a memory to a namespace via `local-brain memory save`. The CLI inserts a row into `~/.local-brain/<namespace>/memories.db` with FTS5 indexing applied immediately.
2. **Embed** — periodically (or on-demand), `local-brain embeddings backfill` reads memories that don't yet have an embedding and writes vectors into a `sqlite-vec` virtual table. Default model is local `all-MiniLM-L6-v2` (384-dim, CPU). Set `LB_EMBEDDING_BACKEND=bedrock` to use **Amazon Titan Embeddings v2** instead.
3. **Search** — `local-brain memory search` runs keyword (FTS5), semantic (sqlite-vec), or hybrid (RRF combination) queries. Returns ranked matches as JSON, ready for any agent to consume.
4. **Recall** — your agent's MCP client (Kiro CLI / Kiro IDE, Claude Code, Cursor) loads relevant memories at session start, or on-demand mid-conversation, via the bundled MCP server.

### AWS-services architecture (Bedrock-optional path)

```mermaid
graph TB
    subgraph "🤖 Agent Runtime"
        Kiro[Kiro CLI / Kiro IDE]
        Claude[Claude Code]
        Cursor[Cursor / other MCP client]
    end

    subgraph "🧠 Local Brain"
        CLI[local-brain CLI]
        MCP[local-brain MCP server]
        Store[(SQLite per-namespace<br/>FTS5 + sqlite-vec)]
    end

    subgraph "🔢 Embedding Backend (configurable)"
        Local[Local sentence-transformers<br/>all-MiniLM-L6-v2 · default]
        Bedrock[Amazon Bedrock<br/>Titan Embeddings v2 · optional]
    end

    Kiro -- MCP --> MCP
    Claude -- MCP --> MCP
    Cursor -- MCP --> MCP
    MCP --> Store
    CLI --> Store
    CLI -.embedding step.-> Local
    CLI -.LB_EMBEDDING_BACKEND=bedrock.-> Bedrock

    style Bedrock fill:#fff3e0
    style Store fill:#e1f5fe
    style MCP fill:#f3e5f5
```

### Where the AI-DLC value lands

| SDLC phase | What Local Brain enables |
|---|---|
| **Implementation** | Agents recall past architectural decisions and code conventions across sessions, reducing rework and inconsistency |
| **Testing** | Agents remember which test fixtures, mock patterns, and skip-rules apply to your codebase |
| **Operation & Maintenance** | Cron-driven memory automations summarize daily activity into searchable insights — "what did I ship last week?" answerable from the agent without scanning git logs |
| **Cross-cutting** | Agents accumulate user preferences ("don't add comments unless requested", "use company X's style guide") that persist across every project |

## Installation

### Prerequisites

- Go 1.26.3 or newer
- Python 3.11+ (for local embedding step) with `pip install sqlite-vec sentence-transformers`
- (Optional) AWS credentials with `bedrock:InvokeModel` permission for Titan Embeddings v2 if using the Bedrock backend

### Build from source

```bash
git clone https://github.com/aws-samples/sample-ai-powered-sdlc-patterns-with-aws.git
cd sample-ai-powered-sdlc-patterns-with-aws/implementation/implement-agent-memory-local-brain
go build -o local-brain ./cmd/local-brain-pp-cli
go build -o local-brain-mcp ./cmd/local-brain-pp-mcp
```

Move the binaries somewhere on your `$PATH` (e.g. `~/bin/` or `/usr/local/bin/`).

### One-time init

```bash
local-brain init
# Creates ~/.local-brain/, vendored embedder script, default config
```

### Wire up your agent (Claude Code example)

Add to `~/.claude.json` under `mcpServers`:
```json
{
  "mcpServers": {
    "local-brain": {
      "command": "local-brain-mcp",
      "args": []
    }
  }
}
```

For Kiro CLI / Kiro IDE, add to `~/.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "local-brain": { "command": "local-brain-mcp", "args": [] }
  }
}
```

## Quick Start

```bash
# 1. Save a memory
local-brain memory save \
  --namespace project/my-app \
  --type insight \
  --content "API gateway uses Cognito JWT in Authorization header, NOT Bearer"

# 2. Search keyword
local-brain memory search "Cognito JWT" --namespace project/my-app

# 3. Generate embeddings (default = local sentence-transformers)
local-brain embeddings backfill --all

# 4. Semantic search
local-brain memory search "how do we authenticate" --namespace project/my-app --mode semantic

# 5. Use Bedrock instead of local model (optional)
export LB_EMBEDDING_BACKEND=bedrock
export AWS_REGION=us-east-1
local-brain embeddings backfill --all
```

## Command Reference

| Command | Description |
|---|---|
| `local-brain init` | One-time setup: creates `~/.local-brain/`, vendors helper scripts, writes default config |
| `local-brain memory save` | Save a memory (insight / decision / outcome / action_item / preference / compiled) to a namespace |
| `local-brain memory list` | List memories in a namespace, most recent first |
| `local-brain memory search` | Search by keyword (FTS5), semantic (sqlite-vec), or hybrid (RRF) |
| `local-brain memory get` | Fetch a single memory by ID, searching across all namespaces if none specified |
| `local-brain memory forget` | Delete a memory by ID |
| `local-brain memory context` | Load all memories for a namespace (alias for list with default limit 50) |
| `local-brain memory dedupe` | Find duplicate memories by content hash across namespaces |
| `local-brain memory patterns` | Find tags appearing across multiple namespaces |
| `local-brain memory bisect` | Show the atomic memories that synthesized a compiled memory |
| `local-brain memory stale` | List action_item memories older than N days |
| `local-brain memory watch` | Tail new memories as they're written (live mode) |
| `local-brain embeddings backfill` | Generate embeddings for memories that don't have them yet |
| `local-brain embeddings status` | Per-namespace coverage report |
| `local-brain embeddings rebuild` | Drop and regenerate embeddings for a namespace |
| `local-brain doctor` | Composite health check (binary, Python deps, sqlite-vec extension, embedder script) |
| `local-brain custom-automation` | Create / update / delete / run-now / logs for user-defined scheduled prompts |
| `local-brain automation memory` | Enable / disable / status of the 9 bundled memory automations (compiler, indexer, linter, etc.) |

Every command supports `--json`, `--select <fields>`, `--dry-run`, and `--no-color`. Pass `--agent` to enable agent-friendly defaults (JSON output, no prompts).

## Memory Types

| Type | Use for |
|---|---|
| `insight` | Facts your agent learned about the code, customer, or domain |
| `decision` | Architectural / design choices, with rationale |
| `outcome` | Results of an action — what shipped, what broke, what got measured |
| `action_item` | Open work items with optional due dates |
| `preference` | User behavior rules ("never edit X without asking", "prefer Y over Z") |
| `compiled` | Synthesized rollups of multiple atomic memories |

## Embedding Backends

Configurable via `LB_EMBEDDING_BACKEND` env var or `~/.local-brain/config.json`:

| Backend | When to use | Cost | Latency |
|---|---|---|---|
| `local` (default) | Privacy-sensitive, offline, free, fast enough for personal scale | $0 | ~30ms / batch on CPU |
| `bedrock` | Higher quality embeddings, no local Python dependency, scales to team usage | ~$0.0001 / 1K tokens (Titan v2) | ~150ms / batch network round-trip |

Local backend uses `sentence-transformers/all-MiniLM-L6-v2` (384-dim).
Bedrock backend uses `amazon.titan-embed-text-v2:0` (configurable to 256/512/1024 dims).

When switching backends, run `local-brain embeddings rebuild --namespace <ns>` — vectors are not interchangeable across models.

## Custom Automations

`local-brain custom-automation` lets you define recurring agent prompts as cron-scheduled tasks. Each automation has:
- A natural-language prompt
- A schedule (`daily@10:07`, `hourly:13`, `weekly:Mon@9:00`)
- An agent invocation template (driven by `LB_AGENT_CLI` and `LB_AGENT_NAME` env vars — point them at your preferred agent runtime)
- A log directory under `~/.local-brain/logs/automations/<id>/`

Example:
```bash
export LB_AGENT_CLI=kiro       # Kiro CLI (or claude-code, cursor, etc.)
export LB_AGENT_NAME=default   # agent profile to invoke

local-brain custom-automation create \
  --name "daily-brief" \
  --prompt "Summarize what I shipped yesterday from git log + memories" \
  --schedule "daily@7:30"

local-brain custom-automation logs daily-brief --tail 200
```

This is the killer pattern for AI-powered SDLC: **the agent runs while you sleep**, the memory grows while you sleep, and the next morning's session starts with yesterday's context already searchable.

## Architecture Files

| Path | Purpose |
|---|---|
| `cmd/local-brain-pp-cli/` | CLI entry point |
| `cmd/local-brain-pp-mcp/` | MCP server entry point |
| `internal/brain/` | SQLite store, FTS5 + sqlite-vec helpers, embedder shell-out |
| `internal/cli/` | Cobra subcommand implementations |
| `internal/cli/scripts/` | Vendored Python embedder + automation runners |
| `internal/mcp/` | MCP tool definitions exposed to agent runtimes |
| `internal/brain/automation/` | Custom automation lifecycle (cron → launchd / systemd) |

## Disclaimer

This is sample code. It is not warranted for production-grade workloads — review the architecture, test under your security model, and adapt to your environment. Embeddings cached on disk include the original text; protect `~/.local-brain/` accordingly. The Bedrock backend requires AWS credentials with `bedrock:InvokeModel` for the configured embedding model — see [AWS Pricing](https://aws.amazon.com/bedrock/pricing/) for cost details.

## License

MIT No Attribution. See [LICENSE](LICENSE).
