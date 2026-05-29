// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceDiffCmd(flags *rootFlags) *cobra.Command {
	var flagSince string

	cmd := &cobra.Command{
		Use:     "diff <namespace>",
		Short:   "Show what changed in a namespace since a given time (transcendence)",
		Example: "  local-brain-pp-cli namespace diff accounts/proofpoint --since 7d --json",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.diff",
			"pp:method":     "GET",
			"pp:path":       "/namespace/diff",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": args[0], "since": flagSince,
				}, flags)
			}
			d, err := brain.Diff(cmd.Context(), args[0], flagSince)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), d, flags)
		},
	}
	cmd.Flags().StringVar(&flagSince, "since", "7d", "Window start (default '7d')")

	return cmd
}
