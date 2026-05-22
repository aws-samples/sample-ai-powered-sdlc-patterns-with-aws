// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryContextCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagLimit int

	cmd := &cobra.Command{
		Use:     "context",
		Short:   "Load all memories for a namespace (alias for list with default limit 50)",
		Example: "  local-brain-pp-cli memory context --namespace projects/local-brain-cli",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.context",
			"pp:method":     "GET",
			"pp:path":       "/memory/context",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run":   true,
					"namespace": flagNamespace,
					"limit":     flagLimit,
				}, flags)
			}
			if flagNamespace == "" {
				return fmt.Errorf("required flag \"namespace\" not set")
			}
			ctx := cmd.Context()
			db, err := brain.OpenReadOnly(ctx, flagNamespace)
			if err != nil {
				return err
			}
			defer db.Close()
			results, err := brain.List(ctx, db, brain.ListOpts{
				Namespace: flagNamespace,
				Limit:     flagLimit,
			})
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespace": flagNamespace,
				"total":     len(results),
				"memories":  results,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Namespace to load")
	cmd.Flags().IntVar(&flagLimit, "limit", 50, "Max memories to return (default 50)")

	return cmd
}
