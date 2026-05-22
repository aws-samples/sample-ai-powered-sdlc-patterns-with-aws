package brain

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// IndexResult is what the rebuild command returns.
type IndexResult struct {
	Path  string `json:"path"`
	Bytes int    `json:"bytes"`
}

// IndexPath returns ~/.local-brain/global/INDEX.md.
func IndexPath() string {
	return filepath.Join(BrainDir(), "global", "INDEX.md")
}

// RebuildIndex regenerates the global index markdown — a TOC of every
// namespace with totals, by-type counts, last-touched, and "needs compilation"
// flags. Mirrors `lb-memory-indexer.sh`'s python core but runs in pure Go.
//
// Always writes to BrainDir/global/INDEX.md so kiro/MCP clients that read
// memories.md per-namespace and INDEX.md for the global TOC have one source
// of truth.
func RebuildIndex(ctx context.Context) (IndexResult, error) {
	all, err := ListNamespaces()
	if err != nil {
		return IndexResult{}, err
	}
	stats, err := Stats(ctx, "", 14)
	if err != nil {
		return IndexResult{}, err
	}
	statByNS := map[string]NamespaceStats{}
	for _, s := range stats {
		statByNS[s.Namespace] = s
	}
	now := time.Now().UTC()

	totalMemories := 0
	totalCompiled := 0
	totalStale := 0
	var needsCompile []string
	for _, ns := range all {
		s := statByNS[ns]
		totalMemories += s.Total
		totalCompiled += s.CompiledCount
		totalStale += len(s.StaleActionItems)
		if s.NeedsCompilation {
			needsCompile = append(needsCompile, ns)
		}
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# Local Brain Index\n\n")
	fmt.Fprintf(&b, "**Generated:** %s\n", now.Format("2006-01-02 15:04 UTC"))
	fmt.Fprintf(&b, "**Total memories:** %d across %d namespaces\n", totalMemories, len(all))
	fmt.Fprintf(&b, "**Compiled narratives:** %d\n", totalCompiled)
	fmt.Fprintf(&b, "**Stale action items:** %d\n", totalStale)
	fmt.Fprintf(&b, "**Namespaces needing compilation:** %d\n\n", len(needsCompile))
	fmt.Fprintf(&b, "## Namespace Summary\n\n")

	sort.Strings(all)
	for _, ns := range all {
		s := statByNS[ns]
		var flags []string
		if s.NeedsCompilation {
			flags = append(flags, "needs-compile")
		}
		if len(s.StaleActionItems) > 0 {
			flags = append(flags, fmt.Sprintf("%d stale-actions", len(s.StaleActionItems)))
		}
		flagStr := ""
		if len(flags) > 0 {
			flagStr = "  [" + strings.Join(flags, " | ") + "]"
		}
		newest := s.Newest
		if len(newest) >= 10 {
			newest = newest[:10]
		}
		// Sort by-type for stable output.
		var typeKeys []string
		for k := range s.ByType {
			typeKeys = append(typeKeys, k)
		}
		sort.Strings(typeKeys)
		var parts []string
		for _, k := range typeKeys {
			parts = append(parts, fmt.Sprintf("%s:%d", k, s.ByType[k]))
		}
		fmt.Fprintf(&b, "### %s\n- **%d memories** | newest: %s%s\n- Types: %s\n\n",
			ns, s.Total, newest, flagStr, strings.Join(parts, ", "))
	}

	if len(needsCompile) > 0 {
		fmt.Fprintf(&b, "## Needs Compilation\n\nThese namespaces have 10+ uncompiled memories:\n\n")
		for _, ns := range needsCompile {
			fmt.Fprintf(&b, "- %s (%d total)\n", ns, statByNS[ns].Total)
		}
		fmt.Fprintln(&b)
	}

	out := []byte(b.String())
	path := IndexPath()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return IndexResult{}, err
	}
	if err := os.WriteFile(path, out, 0o644); err != nil {
		return IndexResult{}, err
	}
	return IndexResult{Path: path, Bytes: len(out)}, nil
}

// ShowIndex returns the rendered index markdown if it exists, or an error.
// Use ShowIndexFiltered to filter by namespace prefix.
func ShowIndex() (string, error) {
	b, err := os.ReadFile(IndexPath())
	if err != nil {
		return "", err
	}
	return string(b), nil
}
