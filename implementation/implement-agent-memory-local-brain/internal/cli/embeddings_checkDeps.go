// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newEmbeddingsCheckDepsCmd(flags *rootFlags) *cobra.Command {
	cmd := &cobra.Command{
		Use:     "check-deps",
		Short:   "Probe candidate Python interpreters for sqlite-vec + sentence-transformers",
		Example: "  local-brain-pp-cli embeddings check-deps --json",
		Annotations: map[string]string{
			"pp:endpoint":   "embeddings.checkDeps",
			"pp:method":     "GET",
			"pp:path":       "/embeddings/check-deps",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			picked, results := brain.ProbePythons()
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"python_bin":          picked,
				"sqlite_vec_available": picked != "",
				"sentence_transformers_available": picked != "",
				"candidates_tried":    results,
			}, flags)
		},
	}
	return cmd
}
