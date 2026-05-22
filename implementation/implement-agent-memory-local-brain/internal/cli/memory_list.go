// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryListCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagLimit int
	var flagType string
	var flagTag string
	var flagSince string
	var flagBefore string

	cmd := &cobra.Command{
		Use:     "list",
		Short:   "List memories in a namespace (most recent first)",
		Example: "  local-brain-pp-cli memory list --namespace global --limit 50",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.list",
			"pp:method":     "GET",
			"pp:path":       "/memory/list",
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
			since, err := brain.ParseSince(flagSince)
			if err != nil {
				return err
			}
			before, err := brain.ParseSince(flagBefore)
			if err != nil {
				return err
			}
			results, err := brain.List(ctx, db, brain.ListOpts{
				Namespace: flagNamespace,
				Types:     brain.SplitCSV(flagType),
				Tags:      brain.SplitCSV(flagTag),
				Since:     since,
				Before:    before,
				Limit:     flagLimit,
			})
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), results, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Namespace to list")
	cmd.Flags().IntVar(&flagLimit, "limit", 50, "Max memories to return (default 50)")
	cmd.Flags().StringVar(&flagType, "type", "", "Filter by memory type (comma-separated)")
	cmd.Flags().StringVar(&flagTag, "tag", "", "Filter by tag (comma-separated, AND-match)")
	cmd.Flags().StringVar(&flagSince, "since", "", "Only memories created after this time")
	cmd.Flags().StringVar(&flagBefore, "before", "", "Only memories created before this time")

	return cmd
}
