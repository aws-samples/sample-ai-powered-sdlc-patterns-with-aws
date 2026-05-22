#!/bin/bash
# lb-memory-embedder.sh (vendored stub)
#
# This is a minimal placeholder. Replace with the production version from:
#
# The production script does the real work:
# 1. Probes 9 candidate Pythons for sqlite-vec + sentence-transformers + load_extension support.
# 2. Reads ~/.local-brain/config.json for embedding_batch_size (default 50).
# 3. Iterates every namespace's memories.db, finds rows missing in memories_vec, embeds, and inserts.
# 4. Writes a JSON result to ~/.local-brain/logs/embedder-output-<ts>.json.
#
# This stub fails loudly so callers know to install the real one.
echo '{"error":"embedder stub — install the real lb-memory-embedder.sh","embedded":0}' >&2
exit 78  # EX_CONFIG
