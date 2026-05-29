// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newMemoryAutomationRunNowCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagForce bool
	var flagWait bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "run-now <name>",
		Short:   "Trigger a memory automation immediately",
		Example: "  local-brain-pp-cli memory-automation run-now compiler --namespace projects/local-brain-cli",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.runNow",
			"pp:method":     "POST",
			"pp:path":       "/automation/memory/{name}/run-now",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			name := args[0]
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "name": name, "namespace": flagNamespace, "force": flagForce, "wait": flagWait,
				}, flags)
			}
			res, err := automation.RunMemoryNow(cmd.Context(), name, flagNamespace, flagForce, flagWait)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Restrict to a namespace (where the automation supports it)")
	cmd.Flags().BoolVar(&flagForce, "force", false, "Bypass the daily lock file")
	cmd.Flags().BoolVar(&flagWait, "wait", false, "Block until the automation completes (default: spawn in background)")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
