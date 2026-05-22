// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newCustomAutomationLogsCmd(flags *rootFlags) *cobra.Command {
	var flagTail int
	var flagFollow bool

	cmd := &cobra.Command{
		Use:     "logs <id>",
		Short:   "Tail logs for a custom automation",
		Example: "  local-brain-pp-cli custom-automation logs daily-briefing --tail 200",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.logs",
			"pp:method":     "GET",
			"pp:path":       "/automation/custom/{id}/logs",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "id": args[0]}, flags)
			}
			res, err := automation.CustomLogs(args[0], flagTail)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().IntVar(&flagTail, "tail", 200, "Lines to tail")
	cmd.Flags().BoolVar(&flagFollow, "follow", false, "Follow")

	return cmd
}
