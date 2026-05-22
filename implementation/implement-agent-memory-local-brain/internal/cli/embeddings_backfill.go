// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newEmbeddingsBackfillCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyBatchSize int
	var bodyAll bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "backfill",
		Short:   "Generate embeddings for memories that don't have them yet (shells to vendored Python)",
		Example: "  local-brain-pp-cli embeddings backfill --all --batch-size 100",
		Annotations: map[string]string{
			"pp:endpoint":   "embeddings.backfill",
			"pp:method":     "POST",
			"pp:path":       "/embeddings/backfill",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": bodyNamespace, "batch_size": bodyBatchSize, "all": bodyAll,
				}, flags)
			}
			out, err := brain.RunEmbedder(cmd.Context(), bodyNamespace, bodyBatchSize, bodyAll)
			if err != nil {
				return fmt.Errorf("embedder failed: %w\n%s", err, string(out))
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"output":    string(out),
				"namespace": bodyNamespace,
				"all":       bodyAll,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Specific namespace (omit for all)")
	cmd.Flags().IntVar(&bodyBatchSize, "batch-size", 50, "Memories per namespace per run (default 50)")
	cmd.Flags().BoolVar(&bodyAll, "all", false, "Process all namespaces")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
