// Hand-rewired in Phase 3.

package cli

import (
	"errors"
	"fmt"
	"os"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newIndexShowCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string
	cmd := &cobra.Command{
		Use:     "show",
		Short:   "Print the current rendered index (markdown by default)",
		Example: "  local-brain-pp-cli index show",
		Annotations: map[string]string{
			"pp:endpoint":   "index.show",
			"pp:method":     "GET",
			"pp:path":       "/index/show",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true}, flags)
			}
			text, err := brain.ShowIndex()
			if err != nil {
				if errors.Is(err, os.ErrNotExist) {
					return fmt.Errorf("no index yet — run `local-brain-pp-cli index rebuild` first")
				}
				return err
			}
			if flags.asJSON {
				return emitJSON(cmd.OutOrStdout(), map[string]any{
					"path":  brain.IndexPath(),
					"bytes": len(text),
				}, flags)
			}
			fmt.Fprint(cmd.OutOrStdout(), text)
			return nil
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Show only entries for namespaces matching this glob")
	return cmd
}
