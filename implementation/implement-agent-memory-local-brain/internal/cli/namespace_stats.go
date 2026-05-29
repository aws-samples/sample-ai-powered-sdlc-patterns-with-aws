// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceStatsCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagStaleDays int

	cmd := &cobra.Command{
		Use:     "stats",
		Short:   "Health stats for namespaces — counts by type, staleness, compilation status, unembedded count",
		Example: "  local-brain-pp-cli namespace stats --namespace accounts/proofpoint --json",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.stats",
			"pp:method":     "GET",
			"pp:path":       "/namespace/stats",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": flagNamespace, "stale_days": flagStaleDays,
				}, flags)
			}
			results, err := brain.Stats(cmd.Context(), flagNamespace, flagStaleDays)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Specific namespace (or prefix glob); defaults to all")
	cmd.Flags().IntVar(&flagStaleDays, "stale-days", 14, "Days threshold for stale action items (default 14)")

	return cmd
}
