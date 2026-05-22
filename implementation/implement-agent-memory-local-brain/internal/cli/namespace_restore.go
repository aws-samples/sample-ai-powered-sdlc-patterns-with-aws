// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceRestoreCmd(flags *rootFlags) *cobra.Command {
	var bodyArchive string
	var bodyRenameTo string
	var bodyMerge bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "restore",
		Short:   "Restore a namespace from a tar.gz archive",
		Example: "  local-brain-pp-cli namespace restore --archive ~/brain-backups/local-brain-backup-20260513-214500.tar.gz --rename-to accounts/restored",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.restore",
			"pp:method":     "POST",
			"pp:path":       "/namespace/restore",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "archive": bodyArchive, "rename_to": bodyRenameTo, "merge": bodyMerge,
				}, flags)
			}
			if bodyArchive == "" {
				return fmt.Errorf("required flag --archive not set")
			}
			n, ns, err := brain.Restore(cmd.Context(), bodyArchive, bodyRenameTo, bodyMerge)
			if err != nil {
				return err
			}
			outNS := ns
			if bodyRenameTo != "" {
				outNS = bodyRenameTo
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"namespace": outNS, "restored": n,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyArchive, "archive", "", "Path to .tar.gz archive")
	cmd.Flags().StringVar(&bodyRenameTo, "rename-to", "", "Restore under a different namespace name")
	cmd.Flags().BoolVar(&bodyMerge, "merge", false, "Merge with existing namespace instead of failing if it exists")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
