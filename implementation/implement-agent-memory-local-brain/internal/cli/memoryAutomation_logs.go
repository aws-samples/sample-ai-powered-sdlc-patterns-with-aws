// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newMemoryAutomationLogsCmd(flags *rootFlags) *cobra.Command {
	var flagTail int
	var flagSince string
	var flagFollow bool

	cmd := &cobra.Command{
		Use:     "logs <name>",
		Short:   "Tail logs for a memory automation",
		Example: "  local-brain-pp-cli memory-automation logs compiler --tail 200",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.logs",
			"pp:method":     "GET",
			"pp:path":       "/automation/memory/{name}/logs",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "name": args[0]}, flags)
			}
			res, err := automation.MemoryLogs(args[0], flagTail, flagSince)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().IntVar(&flagTail, "tail", 200, "Lines to tail (default 200)")
	cmd.Flags().StringVar(&flagSince, "since", "", "Show logs since this time (e.g. '24h')")
	cmd.Flags().BoolVar(&flagFollow, "follow", false, "Follow log output (-f)")

	return cmd
}
