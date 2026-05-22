// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newScheduleUninstallCmd(flags *rootFlags) *cobra.Command {
	var bodyType string
	var bodyName string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "Remove the schedule for an automation",
		Example: "  local-brain-pp-cli schedule uninstall --type memory --name compiler",
		Annotations: map[string]string{
			"pp:endpoint":   "schedule.uninstall",
			"pp:method":     "POST",
			"pp:path":       "/schedule/uninstall",
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
				if err := sched.UninstallMemory(ctx, bodyName); err != nil {
					return err
				}
			case "custom":
				if err := sched.UninstallCustom(ctx, bodyName); err != nil {
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
	cmd.Flags().StringVar(&bodyType, "type", "", "Automation type")
	cmd.Flags().StringVar(&bodyName, "name", "", "Automation name or id")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
