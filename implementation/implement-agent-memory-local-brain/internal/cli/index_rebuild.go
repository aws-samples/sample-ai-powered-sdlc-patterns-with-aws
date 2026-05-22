// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newIndexRebuildCmd(flags *rootFlags) *cobra.Command {
	var stdinBody bool
	cmd := &cobra.Command{
		Use:     "rebuild",
		Short:   "Rebuild ~/.local-brain/global/INDEX.md from current namespace stats",
		Example: "  local-brain-pp-cli index rebuild",
		Annotations: map[string]string{
			"pp:endpoint":   "index.rebuild",
			"pp:method":     "POST",
			"pp:path":       "/index/rebuild",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			res, err := brain.RebuildIndex(cmd.Context())
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")
	return cmd
}
