// Hand-rewired in Phase 3.

package cli

import (
	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryBisectCmd(flags *rootFlags) *cobra.Command {
	var flagWindow string

	cmd := &cobra.Command{
		Use:     "bisect <id>",
		Short:   "Show the atomic memories that were synthesized into a compiled memory (provenance via timestamp/namespace inference) (transcendence)",
		Example: "  local-brain-pp-cli memory bisect mem-20260513-180000-abcd1234 --json",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.bisect",
			"pp:method":     "GET",
			"pp:path":       "/memory/bisect",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "id": args[0], "window": flagWindow,
				}, flags)
			}
			atoms, ns, end, err := brain.Bisect(cmd.Context(), args[0], flagWindow)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"compiled_id":  args[0],
				"namespace":    ns,
				"window":       flagWindow,
				"compiled_at":  end,
				"source_atoms": atoms,
				"count":        len(atoms),
			}, flags)
		},
	}
	cmd.Flags().StringVar(&flagWindow, "window", "7d", "Time window before the compiled memory's created_at to scan (default '7d')")

	return cmd
}
