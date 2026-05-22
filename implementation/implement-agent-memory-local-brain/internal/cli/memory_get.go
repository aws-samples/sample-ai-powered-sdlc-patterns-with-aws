// Hand-rewired in Phase 3.

package cli

import (
	"database/sql"
	"errors"
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryGetCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string

	cmd := &cobra.Command{
		Use:     "get <id>",
		Short:   "Get a single memory by ID, searching across all namespaces if --namespace not given",
		Example: "  local-brain-pp-cli memory get mem-20260513-180000-abcd1234",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.get",
			"pp:method":     "GET",
			"pp:path":       "/memory/{id}",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run":   true,
					"id":        args[0],
					"namespace": flagNamespace,
				}, flags)
			}
			ctx := cmd.Context()
			id := args[0]

			if flagNamespace != "" {
				db, err := brain.OpenReadOnly(ctx, flagNamespace)
				if err != nil {
					return err
				}
				defer db.Close()
				m, err := brain.Get(ctx, db, id)
				if err != nil {
					if errors.Is(err, sql.ErrNoRows) {
						return fmt.Errorf("memory %s not found in %s", id, flagNamespace)
					}
					return err
				}
				m.Namespace = flagNamespace
				return emitJSON(cmd.OutOrStdout(), m, flags)
			}

			m, err := brain.GetAcrossAll(ctx, id)
			if err != nil {
				if errors.Is(err, sql.ErrNoRows) {
					return fmt.Errorf("memory %s not found in any namespace", id)
				}
				return err
			}
			return emitJSON(cmd.OutOrStdout(), m, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Restrict search to a specific namespace")

	return cmd
}
