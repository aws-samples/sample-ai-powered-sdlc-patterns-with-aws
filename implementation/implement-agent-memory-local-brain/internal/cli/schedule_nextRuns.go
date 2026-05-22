// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newScheduleNextRunsCmd(flags *rootFlags) *cobra.Command {
	var flagHours int

	cmd := &cobra.Command{
		Use:     "next-runs",
		Short:   "Show the next N hours of automation fires across launchd + cron in chronological order (transcendence)",
		Example: "  local-brain-pp-cli schedule next-runs --hours 24 --json",
		Annotations: map[string]string{
			"pp:endpoint":   "schedule.nextRuns",
			"pp:method":     "GET",
			"pp:path":       "/schedule/next-runs",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "hours": flagHours}, flags)
			}
			runs, err := sched.NextRuns(cmd.Context(), flagHours)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), runs, flags)
		},
	}
	cmd.Flags().IntVar(&flagHours, "hours", 24, "Window length in hours (default 24)")

	return cmd
}
