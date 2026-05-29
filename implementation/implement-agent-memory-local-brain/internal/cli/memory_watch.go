// Hand-rewired in Phase 3.
//
// Cross-platform polling watcher: on a short interval (1.5s) re-query each
// namespace for memories newer than the last seen created_at timestamp and
// emit any new rows as JSONL. Avoids platform-specific fsevents/inotify code
// at the cost of a tiny scan loop per second; for the typical ~20-namespace
// brain this is well under 1ms per tick.

package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryWatchCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagType string
	var flagInterval time.Duration

	cmd := &cobra.Command{
		Use:     "watch",
		Short:   "Tail new memories as they're written (polling watcher) (transcendence)",
		Example: "  local-brain-pp-cli memory watch --namespace global --type insight",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.watch",
			"pp:method":     "GET",
			"pp:path":       "/memory/watch",
			"mcp:read-only": "true",
			"mcp:hidden":    "true", // streaming/long-running — not a clean MCP tool shape
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": flagNamespace, "type": flagType,
				}, flags)
			}
			ctx := cmd.Context()
			cutoff := time.Now().UTC()
			enc := json.NewEncoder(cmd.OutOrStdout())
			fmt.Fprintf(cmd.ErrOrStderr(), "watching from %s (interval %s)\n", cutoff.Format(time.RFC3339), flagInterval)
			ticker := time.NewTicker(flagInterval)
			defer ticker.Stop()
			for {
				select {
				case <-ctx.Done():
					return nil
				case t := <-ticker.C:
					nss, err := resolveWatchNamespaces(flagNamespace)
					if err != nil {
						return err
					}
					for _, ns := range nss {
						db, err := brain.OpenReadOnly(ctx, ns)
						if err != nil {
							continue
						}
						rows, err := brain.List(ctx, db, brain.ListOpts{
							Namespace: ns,
							Types:     brain.SplitCSV(flagType),
							Since:     cutoff,
							Limit:     50,
						})
						_ = db.Close()
						if err != nil {
							continue
						}
						for _, m := range rows {
							_ = enc.Encode(m)
						}
					}
					cutoff = t.UTC()
				}
			}
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Namespace to watch (default: every namespace)")
	cmd.Flags().StringVar(&flagType, "type", "", "Filter by memory type (comma-separated)")
	cmd.Flags().DurationVar(&flagInterval, "interval", 1500*time.Millisecond, "Poll interval (default 1.5s)")

	return cmd
}

func resolveWatchNamespaces(sel string) ([]string, error) {
	if sel == "" {
		return brain.ListNamespaces()
	}
	all, err := brain.ListNamespaces()
	if err != nil {
		return nil, err
	}
	for _, ns := range all {
		if ns == sel {
			return []string{ns}, nil
		}
	}
	return nil, fmt.Errorf("namespace %q not found", sel)
}

// Compile-time: keep context imported in case the watcher ever needs explicit
// timeout plumbing (currently uses cmd.Context only).
var _ = context.Canceled
