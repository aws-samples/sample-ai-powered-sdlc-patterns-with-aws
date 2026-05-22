// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryPatternsCmd(flags *rootFlags) *cobra.Command {
	var flagMinNamespaces int
	var flagLimit int
	var flagExcludeTag string

	cmd := &cobra.Command{
		Use:     "patterns",
		Short:   "Find tags appearing across multiple namespaces (cross-cutting topics) — exposes the linter's heart on demand (transcendence)",
		Example: "  local-brain-pp-cli memory patterns --min-namespaces 3 --json",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.patterns",
			"pp:method":     "GET",
			"pp:path":       "/memory/patterns",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "min_namespaces": flagMinNamespaces,
				}, flags)
			}
			results, err := brain.Patterns(cmd.Context(), flagMinNamespaces, flagLimit, brain.SplitCSV(flagExcludeTag))
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().IntVar(&flagMinNamespaces, "min-namespaces", 3, "Minimum namespace count for a tag to be reported (default 3)")
	cmd.Flags().IntVar(&flagLimit, "limit", 20, "Max patterns to return (default 20)")
	cmd.Flags().StringVar(&flagExcludeTag, "exclude-tag", "", "Tags to exclude (comma-separated; default 'compiled,auto-generated')")

	return cmd
}
