// Hand-authored Phase 3 command: first-run setup.

package cli

import (
	"embed"
	"io/fs"
	"os"
	"path/filepath"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

//go:embed scripts/lb-memory-*.sh
var vendoredScripts embed.FS

func newInitCmd(flags *rootFlags) *cobra.Command {
	var flagForce bool
	cmd := &cobra.Command{
		Use:     "init",
		Short:   "First-run setup — create ~/.local-brain/, drop vendored automation scripts, write default config",
		Example: "  local-brain-pp-cli init",
		Annotations: map[string]string{
			"pp:endpoint":   "init.run",
			"pp:method":     "POST",
			"pp:path":       "/init",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "force": flagForce}, flags)
			}

			brainDir := brain.BrainDir()
			if err := os.MkdirAll(brainDir, 0o755); err != nil {
				return err
			}
			binDir := filepath.Join(brainDir, "bin")
			if err := os.MkdirAll(binDir, 0o755); err != nil {
				return err
			}

			var written []string
			err := fs.WalkDir(vendoredScripts, "scripts", func(path string, d fs.DirEntry, walkErr error) error {
				if walkErr != nil {
					return walkErr
				}
				if d.IsDir() {
					return nil
				}
				base := filepath.Base(path)
				dst := filepath.Join(binDir, base)
				if !flagForce {
					if _, err := os.Stat(dst); err == nil {
						return nil
					}
				}
				body, err := fs.ReadFile(vendoredScripts, path)
				if err != nil {
					return err
				}
				if err := os.WriteFile(dst, body, 0o755); err != nil {
					return err
				}
				written = append(written, dst)
				return nil
			})
			if err != nil {
				return err
			}

			// Write a default config if it doesn't exist.
			configPath := filepath.Join(brainDir, "cli-config.json")
			if _, err := os.Stat(configPath); os.IsNotExist(err) {
				_ = os.WriteFile(configPath, []byte(`{"embedding_batch_size": 50}`+"\n"), 0o644)
			}

			return emitJSON(cmd.OutOrStdout(), map[string]any{
				"brain_dir":         brainDir,
				"scripts_installed": written,
				"config_path":       configPath,
			}, flags)
		},
	}
	cmd.Flags().BoolVar(&flagForce, "force", false, "Re-overwrite vendored scripts even if they exist")
	return cmd
}
