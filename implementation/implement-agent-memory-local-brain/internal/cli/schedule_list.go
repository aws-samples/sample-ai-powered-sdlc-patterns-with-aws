// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newScheduleListCmd(flags *rootFlags) *cobra.Command {
	var flagType string
	var flagEnabledOnly bool

	cmd := &cobra.Command{
		Use:     "list",
		Short:   "List all schedule entries (memory + custom automations) across launchd and cron",
		Example: "  local-brain-pp-cli schedule list --json",
		Annotations: map[string]string{
			"pp:endpoint":   "schedule.list",
			"pp:method":     "GET",
			"pp:path":       "/schedule",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			entries, err := sched.List(cmd.Context(), flagType, flagEnabledOnly)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), entries, flags)
		},
	}
	cmd.Flags().StringVar(&flagType, "type", "", "Filter by automation type (memory|custom)")
	cmd.Flags().BoolVar(&flagEnabledOnly, "enabled-only", false, "Show only enabled entries")
	return cmd
}
