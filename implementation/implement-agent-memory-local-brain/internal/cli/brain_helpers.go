// Helpers shared by the hand-rewired memory/namespace/embeddings/automation/schedule
// commands. Keeps boilerplate out of every RunE.

package cli

import (
	"encoding/json"
	"fmt"
	"io"
)

// emitJSON marshals v to JSON, applies --select / --compact through
// printJSONFiltered, and writes the result via the framework's flag-aware
// writer. Honors --quiet by silencing output entirely.
//
// Callers that already have a JSON-marshalable shape should use this rather
// than printJSONFiltered directly so future flags (--csv, --plain) Just Work.
func emitJSON(w io.Writer, v any, flags *rootFlags) error {
	if flags.quiet {
		return nil
	}
	if flags.selectFields != "" || flags.compact || flags.asJSON || flags.csv {
		return printJSONFiltered(w, v, flags)
	}
	// Default to pretty JSON when not on a TTY (which is the case for every
	// agent invocation). Human terminal users get the same JSON for now —
	// table rendering for the brain's typed output isn't worth the maintenance
	// cost while the surface is still settling.
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		return fmt.Errorf("encode json: %w", err)
	}
	return nil
}
