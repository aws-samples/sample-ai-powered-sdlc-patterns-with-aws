// Hand-rewired in Phase 3.

package cli

import (
	"os"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newNamespaceBackupCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyDest string
	var bodyAll bool
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "backup",
		Short:   "Backup a namespace (or all) to a tar.gz archive containing db + markdown + embeddings",
		Example: "  local-brain-pp-cli namespace backup --all --dest ~/brain-backups",
		Annotations: map[string]string{
			"pp:endpoint":   "namespace.backup",
			"pp:method":     "POST",
			"pp:path":       "/namespace/backup",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": bodyNamespace, "dest": bodyDest, "all": bodyAll,
				}, flags)
			}
			archive, namespaces, err := brain.Backup(cmd.Context(), bodyNamespace, bodyDest, bodyAll)
			if err != nil {
				return err
			}
			fi, _ := os.Stat(archive)
			var size int64
			if fi != nil {
				size = fi.Size()
			}
			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"archive":    archive,
				"namespaces": namespaces,
				"bytes":      size,
			}, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Specific namespace (omit with --all for full brain backup)")
	cmd.Flags().StringVar(&bodyDest, "dest", "", "Destination directory or .tar.gz path")
	cmd.Flags().BoolVar(&bodyAll, "all", false, "Backup every namespace")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
