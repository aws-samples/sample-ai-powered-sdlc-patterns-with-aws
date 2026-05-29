// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newCustomAutomationStateCmd(flags *rootFlags) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "state <id>",
		Short:   "Get the parsed JSON state from this automation's last run (continuity for next fire)",
		Example: "  local-brain-pp-cli custom-automation state daily-briefing --json",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.state",
			"pp:method":     "GET",
			"pp:path":       "/automation/custom/{id}/state",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "id": args[0]}, flags)
			}
			st, err := automation.CustomState(args[0])
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"id": args[0], "state": st,
			}, flags)
		},
	}
	return cmd
}
