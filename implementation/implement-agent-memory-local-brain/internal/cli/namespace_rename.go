// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceRenameCmd(flags *rootFlags) *cobra.Command {
	var bodyFrom string
	var bodyTo string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "rename",
		Short:   "Rename a namespace (moves the directory; updates markdown header)",
		Example: "  local-brain-pp-cli namespace rename --from accounts/old --to accounts/new",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.rename",
			"pp:method":     "POST",
			"pp:path":       "/namespace/rename",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "from": bodyFrom, "to": bodyTo,
				}, flags)
			}
			if bodyFrom == "" || bodyTo == "" {
				return fmt.Errorf("required flags --from and --to not set")
			}
			n, err := brain.Rename(cmd.Context(), bodyFrom, bodyTo)
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
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
