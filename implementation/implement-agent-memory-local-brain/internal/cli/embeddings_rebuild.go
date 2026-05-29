// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newEmbeddingsRebuildCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyYes bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "rebuild",
		Short:   "Drop and regenerate ALL embeddings for a namespace (use after embedding model change)",
		Example: "  local-brain-pp-cli embeddings rebuild --namespace projects/local-brain-cli --yes",
		Annotations: map[string]string{
			"pp:endpoint":   "embeddings.rebuild",
			"pp:method":     "POST",
			"pp:path":       "/embeddings/rebuild",
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
			if !bodyYes && !flags.yes {
				return fmt.Errorf("destructive: rerun with --yes to confirm dropping the vec table for %s", bodyNamespace)
			}
			n, err := brain.RebuildEmbeddings(cmd.Context(), bodyNamespace)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespace": bodyNamespace,
				"dropped":   n,
				"rebuilt":   0, // backfill is the next step
				"hint":      "run `local-brain-pp-cli embeddings backfill --namespace " + bodyNamespace + "` to repopulate",
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Namespace to rebuild")
	cmd.Flags().BoolVar(&bodyYes, "yes", false, "Confirm destructive operation")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
