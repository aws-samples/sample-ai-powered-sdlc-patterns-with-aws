// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newMemoryAutomationStatusCmd(flags *rootFlags) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "status <name>",
		Short:   "Show last-run timestamp, next-run, locked state, and recent log tail for one automation",
		Example: "  local-brain-pp-cli memory-automation status compiler",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.status",
			"pp:method":     "GET",
			"pp:path":       "/automation/memory/{name}/status",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "name": args[0]}, flags)
			}
			st, err := automation.MemoryStatus(args[0])
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), st, flags)
		},
	}
	return cmd
}
