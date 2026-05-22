// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceVacuumCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyAll bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "vacuum",
		Short:   "Compact (VACUUM) the SQLite database for one or all namespaces; reports bytes saved",
		Example: "  local-brain-pp-cli namespace vacuum --all --json",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.vacuum",
			"pp:method":     "POST",
			"pp:path":       "/namespace/vacuum",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": bodyNamespace, "all": bodyAll,
				}, flags)
			}
			ctx := cmd.Context()
			if bodyAll || bodyNamespace == "" {
				saved, perNS, err := brain.VacuumAll(ctx)
				if err != nil {
					return err
				}
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"namespaces":  perNS,
					"bytes_saved": saved,
				}, flags)
			}
			saved, err := brain.VacuumOne(ctx, bodyNamespace)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespaces": []brain.NamespaceCount{{Namespace: bodyNamespace, Count: int(saved)}},
				"bytes_saved": saved,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Specific namespace (omit for all)")
	cmd.Flags().BoolVar(&bodyAll, "all", false, "Vacuum every namespace")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
