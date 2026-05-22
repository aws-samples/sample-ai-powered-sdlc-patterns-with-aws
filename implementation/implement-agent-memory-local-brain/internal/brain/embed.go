package brain

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

// pythonCandidates mirrors the resolution order in lb-memory-embedder.sh —
// first hit that imports both deps wins. Keep this in sync with the vendored
// script so doctor's claim and the embedder's actual choice always match.
var pythonCandidates = []string{
	"~/.local-brain/.venv/bin/python3",
	"/opt/homebrew/opt/python@3.12/bin/python3.12",
	"/opt/homebrew/opt/python@3.11/bin/python3.11",
	"/opt/homebrew/bin/python3",
	"/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
	"/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
	"python3.12",
	"python3.11",
	"python3",
}

// allowedPythonBinPattern is the strict regex that any candidate must match
// before we will exec it. This is the security boundary between the
// hardcoded pythonCandidates list and the actual exec.Command call below —
// it ensures even if someone mutates pythonCandidates at runtime (which is
// not exposed via any public API) the binary path is constrained to:
//   - absolute paths under common system Python install prefixes, OR
//   - bare names like python3 / python3.11 / python3.12 (looked up via PATH)
// Anything else is rejected before reaching exec.
var allowedPythonBinPattern = regexp.MustCompile(
	`^(/(usr|opt|Library/Frameworks/Python\.framework|Users/[^/]+/\.[^/]+/\.venv)/[a-zA-Z0-9_./-]+/python3(\.[0-9]+)?|python3(\.[0-9]+)?)$`,
)

// validatePythonBin returns the input only if it matches allowedPythonBinPattern.
// Returns empty string on rejection so callers know to skip the candidate.
// This is the explicit input-validator that semgrep + manual review can verify
// constrains the exec target to a safe set, regardless of caller history.
func validatePythonBin(bin string) string {
	if !allowedPythonBinPattern.MatchString(bin) {
		return ""
	}
	return bin
}

// PythonProbeResult describes one candidate's outcome.
type PythonProbeResult struct {
	Bin                          string `json:"bin"`
	SqliteVecOK                  bool   `json:"sqlite_vec_ok"`
	SentenceTransformersOK       bool   `json:"sentence_transformers_ok"`
	SqliteLoadExtensionSupported bool   `json:"sqlite_load_extension_supported"`
	Picked                       bool   `json:"picked"`
	Error                        string `json:"error,omitempty"`
}

// ProbePythons probes each candidate Python interpreter and returns whichever
// one passes the full requirement: sqlite3 with load_extension support PLUS
// sqlite-vec PLUS sentence-transformers. The first pass wins; later
// candidates are still probed (so doctor and check-deps can show all of
// them) but `picked=true` only on the first match.
//
// Each subprocess is capped at 5s to keep doctor under the 10s sample-output
// budget. A typical good candidate completes in ~30-100ms; candidates that
// timeout (e.g., a python that hangs on `import sentence_transformers` because
// of a half-installed venv) are reported with an error rather than blocking
// the whole probe.
func ProbePythons() (string, []PythonProbeResult) {
	probeScript := `
import sqlite3, sys
conn = sqlite3.connect(':memory:')
try:
    conn.enable_load_extension(True)
except (AttributeError, sqlite3.NotSupportedError) as e:
    print('NO_LOADEXT', file=sys.stderr); sys.exit(1)
try:
    import sqlite_vec
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
except Exception as e:
    print('NO_VEC:'+str(e), file=sys.stderr); sys.exit(2)
try:
    import sentence_transformers
except Exception as e:
    print('NO_ST:'+str(e), file=sys.stderr); sys.exit(3)
print('OK')
`
	// Probe all candidates in parallel — 9 subprocesses concurrent costs ~150ms
	// total instead of 1-2s sequential, and lets a single hung interpreter time
	// out without blocking the others.
	type indexed struct {
		idx int
		res PythonProbeResult
	}
	resolved := make([]string, 0, len(pythonCandidates))
	for _, c := range pythonCandidates {
		bin := expandHome(c)
		if !filepath.IsAbs(bin) {
			lp, err := exec.LookPath(bin)
			if err != nil {
				continue
			}
			bin = lp
		}
		if _, err := os.Stat(bin); err != nil {
			continue
		}
		resolved = append(resolved, bin)
	}

	out := make([]PythonProbeResult, len(resolved))
	done := make(chan indexed, len(resolved))
	for i, bin := range resolved {
		go func(i int, bin string) {
			r := PythonProbeResult{Bin: bin}
			probeCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			// Re-validate bin against the strict regex allowlist before exec.
			// This is a defense-in-depth check: pythonCandidates is a static
			// package-level slice never mutated, but explicit validation here
			// makes the data flow obviously safe to readers and static analysis.
			validated := validatePythonBin(bin)
			if validated == "" {
				r.Error = "rejected: bin path did not match allowedPythonBinPattern"
				done <- indexed{i, r}
				return
			}
			data, err := exec.CommandContext(probeCtx, validated, "-c", probeScript).CombinedOutput()
			switch {
			case err == nil:
				r.SqliteLoadExtensionSupported = true
				r.SqliteVecOK = true
				r.SentenceTransformersOK = true
			default:
				msg := strings.TrimSpace(string(data))
				r.Error = msg
				if strings.Contains(msg, "NO_LOADEXT") {
					// nothing usable
				} else if strings.Contains(msg, "NO_VEC") {
					r.SqliteLoadExtensionSupported = true
				} else if strings.Contains(msg, "NO_ST") {
					r.SqliteLoadExtensionSupported = true
					r.SqliteVecOK = true
				}
			}
			done <- indexed{i, r}
		}(i, bin)
	}
	for range resolved {
		x := <-done
		out[x.idx] = x.res
	}
	pickedBin := ""
	for i := range out {
		if out[i].SqliteVecOK && out[i].SentenceTransformersOK && pickedBin == "" {
			out[i].Picked = true
			pickedBin = out[i].Bin
		}
	}
	return pickedBin, out
}

// expandHome turns a leading "~/" into $HOME.
func expandHome(p string) string {
	if strings.HasPrefix(p, "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return p
		}
		return filepath.Join(home, p[2:])
	}
	return p
}

// HealNamespace drops the orphan vec0 shadow tables when the virtual table
// itself is missing. Mirrors server.py:_ensure_vec_table's recovery branch but
// runs without sqlite-vec — pure sqlite. Returns the list of shadow names
// dropped (or that would be dropped, when dryRun=true).
func HealNamespace(ctx context.Context, namespace string, dryRun bool) ([]string, error) {
	db, err := Open(ctx, namespace)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	var hasVec int
	_ = db.QueryRowContext(ctx,
		`SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories_vec' LIMIT 1`).Scan(&hasVec)
	if hasVec == 1 {
		// Healthy already; nothing to drop.
		return nil, nil
	}
	shadows := []string{
		"memories_vec_info",
		"memories_vec_rowids",
		"memories_vec_chunks",
		"memories_vec_vector_chunks00",
	}
	var dropped []string
	for _, s := range shadows {
		var n int
		_ = db.QueryRowContext(ctx,
			`SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1`, s).Scan(&n)
		if n != 1 {
			continue
		}
		if !dryRun {
			if _, err := db.ExecContext(ctx, "DROP TABLE IF EXISTS "+s); err != nil {
				return dropped, err
			}
		}
		dropped = append(dropped, s)
	}
	return dropped, nil
}

// HealAll iterates every namespace and heals each. dryRun reports without
// making changes.
func HealAll(ctx context.Context, dryRun bool) (map[string][]string, int, error) {
	all, err := ListNamespaces()
	if err != nil {
		return nil, 0, err
	}
	out := map[string][]string{}
	total := 0
	for _, ns := range all {
		dropped, err := HealNamespace(ctx, ns, dryRun)
		if err != nil {
			continue
		}
		if len(dropped) > 0 {
			out[ns] = dropped
			total += len(dropped)
		}
	}
	return out, total, nil
}

// RebuildEmbeddings drops the vec table for one namespace so the embedder
// can repopulate from scratch. The embedder script handles re-creation; this
// only handles the wipe step.
func RebuildEmbeddings(ctx context.Context, namespace string) (int, error) {
	db, err := Open(ctx, namespace)
	if err != nil {
		return 0, err
	}
	defer db.Close()
	var dropped int
	tables := []string{
		"memories_vec",
		"memories_vec_info",
		"memories_vec_rowids",
		"memories_vec_chunks",
		"memories_vec_vector_chunks00",
	}
	for _, t := range tables {
		if _, err := db.ExecContext(ctx, "DROP TABLE IF EXISTS "+t); err == nil {
			dropped++
		}
	}
	return dropped, nil
}

// VendoredEmbedderPath returns the expected path of the bundled embedder shell
// script after `local-brain init` ran. Used by `embeddings backfill`.
func VendoredEmbedderPath() string {
	return filepath.Join(BrainDir(), "bin", "lb-memory-embedder.sh")
}

// RunEmbedder shells out to the vendored lb-memory-embedder.sh, returning
// whatever it prints (the script writes JSON to its log dir but also echoes
// progress lines). Returns ErrEmbedderUnavailable when the script is missing.
func RunEmbedder(ctx context.Context, namespace string, batchSize int, all bool) ([]byte, error) {
	script := VendoredEmbedderPath()
	if _, err := os.Stat(script); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("embedder script not installed (run `local-brain-pp-cli init`); expected at %s", script)
		}
		return nil, err
	}
	args := []string{}
	cmd := exec.CommandContext(ctx, "bash", append([]string{script}, args...)...)
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("NEO_MEMORY_EMBEDDER_NAMESPACE=%s", namespace),
		fmt.Sprintf("NEO_MEMORY_EMBEDDER_BATCH_SIZE=%d", batchSize),
		fmt.Sprintf("NEO_MEMORY_EMBEDDER_ALL=%t", all),
	)
	return cmd.CombinedOutput()
}

// SortStrings is a small helper for deterministic outputs — used by tests
// once we add them, and harmless to expose.
func SortStrings(s []string) {
	sort.Strings(s)
}
