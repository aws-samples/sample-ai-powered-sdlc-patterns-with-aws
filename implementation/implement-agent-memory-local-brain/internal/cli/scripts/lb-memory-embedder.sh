#!/bin/bash
# lb-memory-embedder.sh
#
# Backfills vector embeddings for memories that don't have them yet.
# Operates directly on the per-namespace SQLite databases under
# ~/.local-brain/<namespace>/memories.db. Uses sqlite-vec for the virtual
# table and sentence-transformers (all-MiniLM-L6-v2, 384-dim) for the
# embeddings. No external service dependency — invoked by
# `local-brain embeddings backfill` or by the bundled custom-automation
# scheduler.
#
# Configurable via ~/.local-brain/config.json (key: embedding_batch_size,
# default 50).

set -e

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$HOME/.cargo/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export HOME="${HOME:-$(eval echo ~$USER)}"

LOCAL_BRAIN_DIR="$HOME/.local-brain"
LOG_DIR="$LOCAL_BRAIN_DIR/logs"
CONFIG_FILE="$LOCAL_BRAIN_DIR/config.json"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
START_TIME=$(date +%s)

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/memory-embedder.log"
}

log "========================================="
log "Starting Local Brain Memory Embedder"
log "========================================="

if [ ! -d "$LOCAL_BRAIN_DIR" ]; then
    log "ERROR: Local Brain not found at $LOCAL_BRAIN_DIR"
    log "       Run \`local-brain init\` first."
    exit 1
fi

# -----------------------------------------------------------------------------
# Python resolution
# -----------------------------------------------------------------------------
# Picking a Python interpreter that actually has sqlite-vec + sentence-transformers
# is non-trivial because:
#   1. The user may have multiple Python versions installed (system, brew, pyenv,
#      python-build-standalone, etc.).
#   2. Only some of those will have the semantic deps installed.
#   3. macOS python.org builds ship with --disable-loadable-sqlite-extensions,
#      which silently breaks sqlite-vec; we must probe enable_load_extension.
#
# Strategy: try candidates in preference order, probe each one's ability to
# import both deps AND load the sqlite-vec extension, and pick the first that
# passes. If none pass, emit a clear "not installed" warning with the install
# command.
# -----------------------------------------------------------------------------

PYTHON_CANDIDATES=(
    "/opt/homebrew/opt/python@3.12/bin/python3.12"
    "/opt/homebrew/opt/python@3.11/bin/python3.11"
    "/opt/homebrew/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "$HOME/python311/python/bin/python3"
    "python3.12"
    "python3.11"
    "python3"
)

PYTHON_BIN=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
    # Resolve candidate (full path or PATH command)
    if [[ "$candidate" == /* ]]; then
        [[ -x "$candidate" ]] || continue
        bin="$candidate"
    else
        bin=$(command -v "$candidate" 2>/dev/null) || continue
    fi
    # Probe: imports must work AND sqlite3 must support load_extension AND
    # the binary must allow enable_load_extension (disabled in python.org's
    # macOS Python builds shipped without --enable-loadable-sqlite-extensions).
    if "$bin" -c "
import sqlite3, sys
conn = sqlite3.connect(':memory:')
try:
    conn.enable_load_extension(True)
except (AttributeError, sqlite3.NotSupportedError):
    sys.exit(1)
import sqlite_vec
sqlite_vec.load(conn)
conn.enable_load_extension(False)
import sentence_transformers
" 2>/dev/null; then
        PYTHON_BIN="$bin"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    log "WARNING: No Python with sqlite-vec + sentence-transformers found."
    log "         Tried: ${PYTHON_CANDIDATES[*]}"
    log "         Install with:  python3 -m pip install sqlite-vec sentence-transformers"
    RESULT='{"error": "semantic dependencies not installed", "embedded": 0}'
    log "Result: $RESULT"
    log "========================================="
    log "Memory Embedder complete in 0s"
    log "========================================="
    echo "$RESULT" > "$LOG_DIR/embedder-output-$TIMESTAMP.json"
    echo "$RESULT"
    exit 0
fi

log "Python: $PYTHON_BIN"

# Read config (batch size)
BATCH_SIZE=50
if [ -f "$CONFIG_FILE" ]; then
    CONFIGURED_BATCH=$("$PYTHON_BIN" -c "import json; print(json.load(open('$CONFIG_FILE')).get('embedding_batch_size', 50))" 2>/dev/null || echo 50)
    BATCH_SIZE="$CONFIGURED_BATCH"
fi
log "Batch size: $BATCH_SIZE"

# Run the embedder via Python — operates on the SQLite store directly.
set +e
RESULT=$("$PYTHON_BIN" << PYTHON_EOF
import sqlite3, sys, json
from pathlib import Path

LOCAL_BRAIN_DIR = Path.home() / ".local-brain"
batch_size = $BATCH_SIZE

# Deps already validated by shell preflight, but guard anyway
try:
    import sqlite_vec
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(json.dumps({"error": f"semantic dependencies not installed: {e}", "embedded": 0}))
    sys.exit(2)

# Load model once
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(json.dumps({"error": f"model load failed: {str(e)}", "embedded": 0}))
    sys.exit(3)

total_embedded = 0
ns_results = {}

for db_path in sorted(LOCAL_BRAIN_DIR.rglob("memories.db")):
    rel = db_path.parent.relative_to(LOCAL_BRAIN_DIR)
    namespace = str(rel) if str(rel) != "." else "global"

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            # sqlite-vec needs explicit extension loading authorization in
            # Python's sqlite3 (disabled by default for safety).
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            # Check if vec table exists
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories_vec'")
            if not cur.fetchone():
                cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(id TEXT PRIMARY KEY, embedding float[384])")
                conn.commit()

            # Find unembedded memories
            cur.execute("""
                SELECT m.id, m.content, m.tags
                FROM memories m
                LEFT JOIN memories_vec v ON m.id = v.id
                WHERE v.id IS NULL
                LIMIT ?
            """, (batch_size,))
            rows = cur.fetchall()

            if not rows:
                continue

            # Embed batch
            texts = [f"{row[1]} {row[2] or ''}" for row in rows]
            embeddings = model.encode(texts, show_progress_bar=False)

            for i, row in enumerate(rows):
                cur.execute(
                    "INSERT OR REPLACE INTO memories_vec (id, embedding) VALUES (?, ?)",
                    (row[0], embeddings[i].tobytes())
                )

            conn.commit()
            ns_results[namespace] = len(rows)
            total_embedded += len(rows)
        finally:
            conn.close()
    except Exception as e:
        ns_results[namespace] = f"error: {str(e)}"

print(json.dumps({"embedded": total_embedded, "namespaces": ns_results}))
PYTHON_EOF
)
PYTHON_EXIT=$?
set -e

if [ $PYTHON_EXIT -eq 2 ]; then
    log "WARNING: Semantic dependencies not installed — embedder cannot run."
    RESULT='{"error": "semantic dependencies not installed", "embedded": 0}'
elif [ $PYTHON_EXIT -eq 3 ]; then
    log "WARNING: Model load failed — check network or cache."
    RESULT='{"error": "model load failed", "embedded": 0}'
elif [ $PYTHON_EXIT -ne 0 ]; then
    RESULT="{\"error\": \"python exited with code $PYTHON_EXIT\", \"embedded\": 0}"
fi

END_TIME=$(date +%s)
EXECUTION_TIME=$((END_TIME - START_TIME))

log "Result: $RESULT"
log "========================================="
log "Memory Embedder complete in ${EXECUTION_TIME}s"
log "========================================="

# Emit machine-readable result for downstream consumers
echo "$RESULT" > "$LOG_DIR/embedder-output-$TIMESTAMP.json"

# Cleanup old outputs (keep 30 days)
find "$LOG_DIR" -name "embedder-output-*.json" -mtime +30 -delete 2>/dev/null || true

# Final stdout JSON for the calling Go process
echo "$RESULT"
