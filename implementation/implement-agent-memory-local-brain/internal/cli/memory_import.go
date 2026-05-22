// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryImportCmd(flags *rootFlags) *cobra.Command {
	var bodyFile string
	var bodyNamespace string
	var bodyFormat string
	var bodyDedupeBy string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "import",
		Short:   "Import memories from a file (JSON array, JSONL, or markdown)",
		Example: "  local-brain-pp-cli memory import --file backup.jsonl --namespace global",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.import",
			"pp:method":     "POST",
			"pp:path":       "/memory/import",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "file": bodyFile, "namespace": bodyNamespace, "format": bodyFormat,
				}, flags)
			}
			if bodyFile == "" {
				return fmt.Errorf("required flag --file not set")
			}
			res, err := brain.ImportFile(cmd.Context(), bodyFile, bodyFormat, bodyNamespace, bodyDedupeBy)
			if err != nil {
				return err
			}
			return emitJSON(cmd.OutOrStdout(), res, flags)
		},
	}
	cmd.Flags().StringVar(&bodyFile, "file", "", "Path to file to import (use '-' for stdin)")
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Override target namespace (defaults to memory's own namespace field)")
	cmd.Flags().StringVar(&bodyFormat, "format", "", "File format: json, jsonl, markdown (default: auto-detect from extension)")
	cmd.Flags().StringVar(&bodyDedupeBy, "dedupe-by", "hash", "Skip imports whose 'hash' or 'id' already exists (default: hash)")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
