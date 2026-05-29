// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

// defaultMemorySchedules mirrors the cron timings baked into the
// lb-memory-*.sh + their .plist twins in the public catalog. When a user calls
// `enable <name>` we apply these by default; pass --schedule to override.
var defaultMemorySchedules = map[string]string{
	"embedder":           "every-30m",
	"indexer":            "daily@03:30",
	"compiler":           "daily@04:00",
	"linter":             "weekly@sunday-05:00",
	"enricher":           "weekly@monday-05:30",
	"pruner":             "weekly@sunday-21:00",
	"rollup":             "daily@06:00",
	"exporter":           "daily@22:00",
	"migrate-namespaces": "daily@02:30",
}

func newMemoryAutomationEnableCmd(flags *rootFlags) *cobra.Command {
	var flagSchedule string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "enable <name>",
		Short:   "Install the launchd plist (macOS) or crontab entry (Linux/WSL) so this automation runs on its schedule",
		Example: "  local-brain-pp-cli memory-automation enable compiler",
		Annotations: map[string]string{
			"pp:endpoint":   "memoryAutomation.enable",
			"pp:method":     "POST",
			"pp:path":       "/automation/memory/{name}/enable",
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
			schedule := flagSchedule
			if schedule == "" {
				schedule = defaultMemorySchedules[name]
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "name": name, "schedule": schedule,
				}, flags)
			}
			if err := sched.InstallMemory(cmd.Context(), name, schedule); err != nil {
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
	cmd.Flags().StringVar(&flagSchedule, "schedule", "", "Schedule spec override (default: built-in for this automation)")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
