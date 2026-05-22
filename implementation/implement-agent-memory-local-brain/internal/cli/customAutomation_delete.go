// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newCustomAutomationDeleteCmd(flags *rootFlags) *cobra.Command {
	var flagKeepLogs bool

	cmd := &cobra.Command{
		Use:     "delete <id>",
		Short:   "Delete a custom automation (removes plist/cron + dir)",
		Example: "  local-brain-pp-cli custom-automation delete daily-briefing --yes",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.delete",
			"pp:method":     "DELETE",
			"pp:path":       "/automation/custom/{id}",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			id := args[0]
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "id": id}, flags)
			}
			_ = sched.UninstallCustom(cmd.Context(), id)
			if err := automation.DeleteCustom(id, flagKeepLogs); err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"id": id, "deleted": true,
			}, flags)
		},
	}
	cmd.Flags().BoolVar(&flagKeepLogs, "keep-logs", false, "Preserve the log directory")

	return cmd
}
