// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain/automation"

	"github.com/spf13/cobra"
)

func newCustomAutomationListCmd(flags *rootFlags) *cobra.Command {
	var flagEnabledOnly bool
	var flagFilter string

	cmd := &cobra.Command{
		Use:     "list",
		Short:   "List all custom automations with status",
		Example: "  local-brain-pp-cli custom-automation list --enabled-only --json",
		Annotations: map[string]string{
			"pp:endpoint":   "customAutomation.list",
			"pp:method":     "GET",
			"pp:path":       "/automation/custom",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			autos, err := automation.ListCustom(flagEnabledOnly, flagFilter)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), autos, flags)
		},
	}
	cmd.Flags().BoolVar(&flagEnabledOnly, "enabled-only", false, "Show only enabled automations")
	cmd.Flags().StringVar(&flagFilter, "filter", "", "Substring filter on name")
	return cmd
}
