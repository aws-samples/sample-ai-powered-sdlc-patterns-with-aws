// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceDeleteCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string

	cmd := &cobra.Command{
		Use:     "delete",
		Short:   "Delete an entire namespace (db, markdown, embeddings — irreversible)",
		Example: "  local-brain-pp-cli namespace delete --namespace work/scratch --yes",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.delete",
			"pp:method":     "DELETE",
			"pp:path":       "/namespace/delete",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": bodyNamespace,
				}, flags)
			}
			if bodyNamespace == "" {
				return fmt.Errorf("required flag --namespace not set")
			}
			if !flags.yes {
				return fmt.Errorf("destructive: rerun with --yes to confirm deletion of %s", bodyNamespace)
			}
			if err := brain.DeleteNamespace(bodyNamespace); err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespace": bodyNamespace, "deleted": true,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Namespace to delete")

	return cmd
}
