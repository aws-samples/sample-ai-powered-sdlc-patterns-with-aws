// Copyright 2026 abhijit-karode. Licensed under Apache-2.0. See LICENSE.
// Hand-rewired in Phase 3 to call internal/brain directly instead of HTTP.

package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newMemorySaveCmd(flags *rootFlags) *cobra.Command {
	var bodyNamespace string
	var bodyType string
	var bodyContent string
	var bodyTags string
	var bodySource string
	var bodyRotateTag string
	var stdinBody bool

	cmd := &cobra.Command{
		Use:     "save",
		Short:   "Save a memory (insight, decision, outcome, action_item, preference, or compiled) to a namespace",
		Example: "  local-brain-pp-cli memory save --namespace projects/local-brain-cli --type insight --content 'CLI v0.1.0 shipped'",
		Annotations: map[string]string{
			"pp:endpoint":   "memory.save",
			"pp:method":     "POST",
			"pp:path":       "/memory/save",
			"mcp:read-only": "false",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if stdinBody {
				stdinData, err := io.ReadAll(os.Stdin)
				if err != nil {
					return fmt.Errorf("reading stdin: %w", err)
				}
				var body struct {
					Namespace string `json:"namespace"`
					Type      string `json:"type"`
					Content   string `json:"content"`
					Tags      string `json:"tags"`
					Source    string `json:"source"`
					RotateTag string `json:"rotateTag"`
				}
				if err := json.Unmarshal(stdinData, &body); err != nil {
					return fmt.Errorf("parsing stdin JSON: %w", err)
				}
				bodyNamespace = body.Namespace
				bodyType = body.Type
				bodyContent = body.Content
				bodyTags = body.Tags
				bodySource = body.Source
				bodyRotateTag = body.RotateTag
			}

			if dryRunOK(flags) {
				envelope := map[string]any{
					"dry_run":   true,
					"namespace": bodyNamespace,
					"type":      bodyType,
					"content":   bodyContent,
				}
				return emitJSON(cmd.OutOrStdout(), envelope, flags)
			}

			if bodyNamespace == "" {
				return fmt.Errorf("required flag \"namespace\" not set")
			}
			if bodyContent == "" {
				return fmt.Errorf("required flag \"content\" not set")
			}

			ctx := cmd.Context()
			db, err := brain.Open(ctx, bodyNamespace)
			if err != nil {
				return err
			}
			defer db.Close()

			rotated := 0
			if bodyRotateTag != "" {
				n, err := brain.RotateTagDelete(ctx, db, bodyRotateTag)
				if err != nil {
					return fmt.Errorf("rotate-tag cleanup: %w", err)
				}
				rotated = n
			}

			m := &brain.Memory{
				Type:    bodyType,
				Content: bodyContent,
				Tags:    bodyTags,
				Source:  bodySource,
			}
			id, err := brain.Save(ctx, db, bodyNamespace, m)
			if err != nil {
				// Save still returns the ID when only the markdown mirror failed —
				// surface that as a warning, not a hard failure.
				if id != "" {
					fmt.Fprintln(os.Stderr, "warning:", err)
				} else {
					return err
				}
			}
			result := map[string]any{
				"id":        id,
				"namespace": bodyNamespace,
				"saved":     true,
				"rotated":   rotated,
			}
			return emitJSON(cmd.OutOrStdout(), result, flags)
		},
	}
	cmd.Flags().StringVar(&bodyNamespace, "namespace", "", "Namespace to save to (e.g. 'accounts/acme', 'global', 'projects/x')")
	cmd.Flags().StringVar(&bodyType, "type", "", "Memory type — one of: insight, decision, outcome, action_item, preference, compiled (default: insight)")
	cmd.Flags().StringVar(&bodyContent, "content", "", "The memory content (use --editor to open $EDITOR for long-form)")
	cmd.Flags().StringVar(&bodyTags, "tags", "", "Comma-separated tags")
	cmd.Flags().StringVar(&bodySource, "source", "", "Where this memory came from (e.g. 'meeting 2026-05-13', 'CR-274381507')")
	cmd.Flags().StringVar(&bodyRotateTag, "rotate-tag", "", "If set, delete any existing memories in this namespace whose tags contain this rotation key before saving")
	cmd.Flags().BoolVar(&stdinBody, "stdin", false, "Read request body as JSON from stdin")

	return cmd
}
