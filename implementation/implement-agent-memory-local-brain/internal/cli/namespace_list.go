// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceListCmd(flags *rootFlags) *cobra.Command {
	var flagFilter string

	cmd := &cobra.Command{
		Use:     "list",
		Short:   "List all namespaces with memory counts",
		Example: "  local-brain-pp-cli namespace list --json",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.list",
			"pp:method":     "GET",
			"pp:path":       "/namespace/list",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "filter": flagFilter,
				}, flags)
			}
			results, err := brain.NamespaceList(cmd.Context(), flagFilter)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().StringVar(&flagFilter, "filter", "", "Glob filter (e.g. 'accounts/*')")

	return cmd
}
