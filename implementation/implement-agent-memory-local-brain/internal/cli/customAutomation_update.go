// Hand-rewired in Phase 3.

package cli

import (
	"path/filepath"

	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newCustomAutomationUpdateCmd(flags *rootFlags) *cobra.Command {
	var bodyPrompt string
	var bodySchedule string
	var bodyEnabled bool
	var bodyAgent string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "update <id>",
		Short:   "Update an existing custom automation",
		Example: "  local-brain-pp-cli custom-automation update daily-briefing --schedule daily@10:30",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.update",
			"pp:method":     "POST",
			"pp:path":       "/automation/custom/{id}",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			id := args[0]
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "id": id, "schedule": bodySchedule,
				}, flags)
			}
			opts := automation.UpdateCustomOpts{
				Prompt: bodyPrompt, Schedule: bodySchedule, Agent: bodyAgent,
			}
			if cmd.Flags().Changed("enabled") {
				opts.Enabled = &bodyEnabled
			}
			c, err := automation.UpdateCustom(id, opts)
			if err != nil {
				return err
			}
			// Reinstall schedule when schedule or enabled flag changed.
			if bodySchedule != "" || cmd.Flags().Changed("enabled") {
				_ = sched.UninstallCustom(cmd.Context(), id)
				if c.Enabled {
					runScript := filepath.Join(automation.TaskDir(id), "run.sh")
					_ = sched.InstallCustom(cmd.Context(), id, runScript, bodySchedule)
				}
			}
			return emitJSON(cmd.OutOrStdout(), c, flags)
		},
	}
	cmd.Flags().StringVar(&bodyPrompt, "prompt", "", "New prompt")
	cmd.Flags().StringVar(&bodySchedule, "schedule", "", "New schedule spec")
	cmd.Flags().BoolVar(&bodyEnabled, "enabled", false, "Enable or disable")
	cmd.Flags().StringVar(&bodyAgent, "agent", "", "Agent name (passed to LB_AGENT_CLI)")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
