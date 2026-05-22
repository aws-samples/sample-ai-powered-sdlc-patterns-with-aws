// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceMoveCmd(flags *rootFlags) *cobra.Command {
	var bodyFrom string
	var bodyTo string
	var bodyType string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "move",
		Short:   "Move memories from one namespace to another (preserving IDs and metadata)",
		Example: "  local-brain-pp-cli namespace move --from work/old --to work/new --type insight",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.move",
			"pp:method":     "POST",
			"pp:path":       "/namespace/move",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "from": bodyFrom, "to": bodyTo, "type": bodyType,
				}, flags)
			}
			if bodyFrom == "" || bodyTo == "" {
				return fmt.Errorf("required flags --from and --to not set")
			}
			n, err := brain.Move(cmd.Context(), bodyFrom, bodyTo, bodyType)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"from": bodyFrom, "to": bodyTo, "moved": n,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyFrom, "from", "", "Source namespace")
	cmd.Flags().StringVar(&bodyTo, "to", "", "Target namespace")
	cmd.Flags().StringVar(&bodyType, "type", "", "Only move memories of this type")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
