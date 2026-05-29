// Hand-rewired in Phase 3.

package cli

import (
	"fmt"
	"path/filepath"

	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newScheduleInstallCmd(flags *rootFlags) *cobra.Command {
	var bodyType string
	var bodyName string
	var bodySchedule string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "install",
		Short:   "Idempotently install the schedule for a memory or custom automation",
		Example: "  local-brain-pp-cli schedule install --type memory --name compiler",
		Annotations: map[string]string{
			"pp:endpoint":   "schedule.install",
			"pp:method":     "POST",
			"pp:path":       "/schedule/install",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "type": bodyType, "name": bodyName,
				}, flags)
			}
			if bodyType == "" || bodyName == "" {
				return fmt.Errorf("required flags --type and --name not set")
			}
			ctx := cmd.Context()
			switch bodyType {
			case "memory":
				schedule := bodySchedule
				if schedule == "" {
					schedule = defaultMemorySchedules[bodyName]
				}
				if err := sched.InstallMemory(ctx, bodyName, schedule); err != nil {
					return err
				}
			case "custom":
				runScript := filepath.Join(automation.TaskDir(bodyName), "run.sh")
				if err := sched.InstallCustom(ctx, bodyName, runScript, bodySchedule); err != nil {
					return err
				}
			default:
				return fmt.Errorf("unknown type %q (memory|custom)", bodyType)
			}
			plat := "cron"
			if sched.IsMacOS() {
				plat = "launchd"
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"name": bodyName, "type": bodyType, "platform": plat, "success": true,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyType, "type", "", "Automation type (memory|custom)")
	cmd.Flags().StringVar(&bodyName, "name", "", "Automation name or id")
	cmd.Flags().StringVar(&bodySchedule, "schedule", "", "Schedule spec override")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
