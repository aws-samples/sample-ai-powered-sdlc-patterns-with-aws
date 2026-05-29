// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newEmbeddingsHealShadowTablesCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyAll bool
	var bodyDryRun bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "heal-shadow-tables",
		Short:   "Drop orphaned sqlite-vec shadow tables left by a crashed backfill (transcendence)",
		Example: "  local-brain-pp-cli embeddings heal-shadow-tables --all --dry-run --json",
		Annotations: map[string]string{
			"pp:endpoint":   "embeddings.healShadowTables",
			"pp:method":     "POST",
			"pp:path":       "/embeddings/heal-shadow-tables",
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
				healed, total, err := brain.HealAll(ctx, bodyDryRun)
				if err != nil {
					return err
				}
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"namespaces_healed": healed,
					"orphans_dropped":   total,
					"dry_run":           bodyDryRun,
				}, flags)
			}
			dropped, err := brain.HealNamespace(ctx, bodyNamespace, bodyDryRun)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespaces_healed": map[string][]string{bodyNamespace: dropped},
				"orphans_dropped":   len(dropped),
				"dry_run":           bodyDryRun,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Specific namespace (omit with --all for every namespace)")
	cmd.Flags().BoolVar(&bodyAll, "all", false, "Heal every namespace")
	cmd.Flags().BoolVar(&bodyDryRun, "dry-run", false, "Show what would be dropped without actually dropping")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
