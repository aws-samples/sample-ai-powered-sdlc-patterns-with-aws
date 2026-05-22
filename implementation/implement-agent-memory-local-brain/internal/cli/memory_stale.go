// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryStaleCmd(flags *rootFlags) *cobra.Command {
	var flagDays int
	var flagType string
	var flagNamespace string
	var flagLimit int

	cmd := &cobra.Command{
		Use:     "stale",
		Short:   "List action_item memories older than N days across every namespace (transcendence)",
		Example: "  local-brain-pp-cli memory stale --days 14 --json --select id,namespace,content,age_days",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.stale",
			"pp:method":     "GET",
			"pp:path":       "/memory/stale",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "days": flagDays, "type": flagType, "namespace": flagNamespace,
				}, flags)
			}
			results, err := brain.Stale(cmd.Context(), flagNamespace, flagType, flagDays, flagLimit)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().IntVar(&flagDays, "days", 14, "Days of age threshold (default 14)")
	cmd.Flags().StringVar(&flagType, "type", "action_item", "Memory type to filter (default: action_item)")
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Limit to a namespace prefix")
	cmd.Flags().IntVar(&flagLimit, "limit", 100, "Max results")

	return cmd
}
