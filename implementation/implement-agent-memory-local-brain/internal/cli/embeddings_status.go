// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newEmbeddingsStatusCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string

	cmd := &cobra.Command{
		Use:     "status",
		Short:   "Per-namespace embedding coverage — % embedded, age of oldest unembedded (transcendence)",
		Example: "  local-brain-pp-cli embeddings status --json",
		Annotations: map[string]string{
			"pp:endpoint":   "embeddings.status",
			"pp:method":     "GET",
			"pp:path":       "/embeddings/status",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": flagNamespace,
				}, flags)
			}
			results, err := brain.EmbedStatus(cmd.Context(), flagNamespace)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Specific namespace (or prefix glob)")

	return cmd
}
