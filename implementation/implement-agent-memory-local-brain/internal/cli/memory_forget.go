// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryForgetCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string

	cmd := &cobra.Command{
		Use:     "forget <id>",
		Short:   "Delete a memory by ID (also removes its embedding row and regenerates the namespace markdown mirror)",
		Example: "  local-brain-pp-cli memory forget mem-20260513-180000-abcd1234 --yes",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.forget",
			"pp:method":     "DELETE",
			"pp:path":       "/memory/{id}",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			id := args[0]
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run":   true,
					"id":        id,
					"namespace": flagNamespace,
				}, flags)
			}
			ctx := cmd.Context()
			if flagNamespace != "" {
				db, err := brain.Open(ctx, flagNamespace)
				if err != nil {
					return err
				}
				defer db.Close()
				ok, err := brain.Forget(ctx, db, flagNamespace, id)
				if err != nil {
					return err
				}
				if !ok {
					return fmt.Errorf("memory %s not found in %s", id, flagNamespace)
				}
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"id": id, "namespace": flagNamespace, "deleted": true,
				}, flags)
			}
			ns, ok, err := brain.ForgetAcrossAll(ctx, id)
			if err != nil {
				return err
			}
			if !ok {
				return fmt.Errorf("memory %s not found in any namespace", id)
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"id": id, "namespace": ns, "deleted": true,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Restrict to a specific namespace (otherwise searches all)")

	return cmd
}
