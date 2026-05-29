// Hand-rewired in Phase 3 to call internal/brain directly.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemorySearchCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagMode string
	var flagLimit int
	var flagType string
	var flagTag string
	var flagSince string
	var flagBefore string
	var flagThreshold float64

	cmd := &cobra.Command{
		Use:     "search <query>",
		Short:   "Search memories by keyword (FTS5), semantic similarity (sqlite-vec), or hybrid",
		Example: "  local-brain-pp-cli memory search 'sentral CLI' --json --select id,namespace,score,content",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.search",
			"pp:method":     "GET",
			"pp:path":       "/memory/search",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run":   true,
					"query":     args[0],
					"namespace": flagNamespace,
					"mode":      flagMode,
					"limit":     flagLimit,
				}, flags)
			}
			results, err := brain.Search(cmd.Context(), brain.SearchOpts{
				Query:     args[0],
				Namespace: flagNamespace,
				Mode:      flagMode,
				Limit:     flagLimit,
				Types:     brain.SplitCSV(flagType),
				Tags:      brain.SplitCSV(flagTag),
				Threshold: flagThreshold,
			})
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Limit search to a specific namespace (or namespace prefix glob like 'accounts/*')")
	cmd.Flags().StringVar(&flagMode, "mode", "auto", "Search mode: auto, keyword, semantic, hybrid (default: auto)")
	cmd.Flags().IntVar(&flagLimit, "limit", 20, "Max results (default 20)")
	cmd.Flags().StringVar(&flagType, "type", "", "Filter by memory type (comma-separated for multiple)")
	cmd.Flags().StringVar(&flagTag, "tag", "", "Filter by tag (comma-separated; AND-match)")
	cmd.Flags().StringVar(&flagSince, "since", "", "Only memories created after this time (e.g. '2h', '24h', '7d', '2026-01-01')")
	cmd.Flags().StringVar(&flagBefore, "before", "", "Only memories created before this time")
	cmd.Flags().Float64Var(&flagThreshold, "threshold", 1.0, "Distance threshold for semantic mode (lower = stricter; default 1.0)")

	return cmd
}
