// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryDedupeCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagApply bool

	cmd := &cobra.Command{
		Use:     "dedupe",
		Short:   "Find duplicate memories by content hash across namespaces (transcendence)",
		Example: "  local-brain-pp-cli memory dedupe --apply --json",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.dedupe",
			"pp:method":     "GET",
			"pp:path":       "/memory/dedupe",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": flagNamespace, "apply": flagApply,
				}, flags)
			}
			groups, err := brain.Dedupe(cmd.Context(), flagNamespace, flagApply)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), groups, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Limit to a namespace prefix")
	cmd.Flags().BoolVar(&flagApply, "apply", false, "If true, delete duplicates (keep the oldest); else dry-run")

	return cmd
}
