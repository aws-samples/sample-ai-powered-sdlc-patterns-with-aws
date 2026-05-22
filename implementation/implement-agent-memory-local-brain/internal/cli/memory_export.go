// Hand-rewired in Phase 3.

package cli

import (
	"fmt"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemoryExportCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	var flagFormat string
	var flagIncludeEmbeddings bool
	var flagType string

	cmd := &cobra.Command{
		Use:     "export",
		Short:   "Export memories from a namespace (alias to namespace export)",
		Example: "  local-brain-pp-cli memory export --namespace projects/local-brain-cli --format jsonl > brain.jsonl",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.export",
			"pp:method":     "GET",
			"pp:path":       "/memory/export",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"dry_run": true, "namespace": flagNamespace, "format": flagFormat,
				}, flags)
			}
			if flagNamespace == "" {
				return fmt.Errorf("required flag --namespace not set")
			}
			res, err := brain.ExportNamespace(cmd.Context(), flagNamespace, flagFormat, flagIncludeEmbeddings, flagType, cmd.OutOrStdout())
			if err != nil {
				return err
			}
			// Print summary to stderr so the export stream itself stays clean.
			fmt.Fprintf(cmd.ErrOrStderr(), "exported %d bytes (%s) from %s\n", res.Bytes, res.Format, res.Namespace)
			return nil
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Namespace to export")
	cmd.Flags().StringVar(&flagFormat, "format", "json", "Output format: json, jsonl, markdown, csv (default: json)")
	cmd.Flags().BoolVar(&flagIncludeEmbeddings, "include-embeddings", false, "Include embedding vectors (large; default false)")
	cmd.Flags().StringVar(&flagType, "type", "", "Filter by memory type")

	return cmd
}
