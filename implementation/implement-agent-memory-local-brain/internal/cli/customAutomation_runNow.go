// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newCustomAutomationRunNowCmd(flags *rootFlags) *cobra.Command {
	var flagWait bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "run-now <id>",
		Short:   "Trigger a custom automation immediately",
		Example: "  local-brain-pp-cli custom-automation run-now daily-briefing",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.runNow",
			"pp:method":     "POST",
			"pp:path":       "/automation/custom/{id}/run-now",
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
			res, err := automation.RunCustomNow(cmd.Context(), id, flagWait)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().BoolVar(&flagWait, "wait", false, "Block until completion")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
