// Hand-rewired in Phase 3.

package cli

import (
	"os"
	"path/filepath"

	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"

	"github.com/spf13/cobra"
)

func newCustomAutomationCreateCmd(flags *rootFlags) *cobra.Command {
	var bodyName string
	var bodyPrompt string
	var bodySchedule string
	var bodyAgent string
	var bodyDeliveryEmail bool
	var bodyDeliverySlack bool
	var bodyDeliveryWorkspace bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "create",
		Short:   "Create a new custom automation (writes run.sh + plist/cron entry)",
		Example: "  local-brain-pp-cli custom-automation create --name 'Daily Briefing' --prompt 'Generate today briefing' --schedule daily@10:07",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.create",
			"pp:method":     "POST",
			"pp:path":       "/automation/custom",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "name": bodyName, "schedule": bodySchedule,
				}, flags)
			}
			c, err := automation.CreateCustom(automation.CreateCustomOpts{
				Name: bodyName, Prompt: bodyPrompt, Schedule: bodySchedule, Agent: bodyAgent,
				DeliveryEmail: bodyDeliveryEmail, DeliverySlack: bodyDeliverySlack,
				DeliveryWorkspace: bodyDeliveryWorkspace,
			})
			if err != nil {
				return err
			}
			runScript := filepath.Join(automation.TaskDir(c.ID), "run.sh")
			if err := sched.InstallCustom(cmd.Context(), c.ID, runScript, bodySchedule); err != nil {
				// Schedule install failure shouldn't roll back the create — surface a warning.
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"automation": c,
					"warning":    "schedule install failed: " + err.Error(),
				}, flags)
			}
			return emitJSON(cmd.OutOrStdout(), c, flags)
		},
	}
	cmd.Flags().StringVar(&bodyName, "name", "", "Human-readable name (will be slugified to id)")
	cmd.Flags().StringVar(&bodyPrompt, "prompt", "", "Agent CLI prompt to execute on schedule (use --editor for long prompts)")
	cmd.Flags().StringVar(&bodySchedule, "schedule", "daily@08:00", "Schedule spec — daily@08:00, weekly@monday-09:00, hourly@:30, every-15m, or a raw cron expression")
	cmd.Flags().StringVar(&bodyAgent, "agent", os.Getenv("LB_AGENT_NAME"), "Agent name to invoke via LB_AGENT_CLI (defaults to LB_AGENT_NAME env or empty)")
	cmd.Flags().BoolVar(&bodyDeliveryEmail, "delivery-email", false, "Append 'email the results' to the prompt")
	cmd.Flags().BoolVar(&bodyDeliverySlack, "delivery-slack", false, "Append 'send results via Slack DM' to the prompt")
	cmd.Flags().BoolVar(&bodyDeliveryWorkspace, "delivery-workspace", true, "Save outputs to ~/Documents/neo-workspace (default true)")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
