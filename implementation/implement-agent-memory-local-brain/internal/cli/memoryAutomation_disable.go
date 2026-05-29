// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newMemoryAutomationDisableCmd(flags *rootFlags) *cobra.Command {
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "disable <name>",
		Short:   "Uninstall the launchd plist or crontab entry for this automation",
		Example: "  local-brain-pp-cli memory-automation disable compiler",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.disable",
			"pp:method":     "POST",
			"pp:path":       "/automation/memory/{name}/disable",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			name := args[0]
			if !automation.IsValidMemoryName(name) {
				return fmt.Errorf("unknown memory automation %q", name)
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "name": name}, flags)
			}
			if err := sched.UninstallMemory(cmd.Context(), name); err != nil {
				return err
			}
			plat := "cron"
			if sched.IsMacOS() {
				plat = "launchd"
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"name": name, "platform": plat, "success": true,
			}, flags)
		},
	}
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
