// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newMemoryAutomationListCmd(flags *rootFlags) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "list",
		Short:   "List the 9 memory automations with current status (last-run, next-run, locked, enabled)",
		Example: "  local-brain-pp-cli memory-automation list --json",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.list",
			"pp:method":     "GET",
			"pp:path":       "/automation/memory",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			ctx := cmd.Context()
			autos, err := automation.ListMemoryAutomations()
			if err != nil {
				return err
			}
			// Merge schedule data so the listing shows enabled/cron expressions too.
			entries, _ := sched.List(ctx, "memory", false)
			byName := map[string]sched.Entry{}
			for _, e := range entries {
				byName[e.Name] = e
			}
			for i := range autos {
				if e, ok := byName[autos[i].Name]; ok {
					autos[i].Enabled = e.Enabled
					autos[i].Schedule = e.CronExpr
				}
			}
			return emitJSON(cmd.OutOrStdout(), autos, flags)
		},
	}
	return cmd
}
