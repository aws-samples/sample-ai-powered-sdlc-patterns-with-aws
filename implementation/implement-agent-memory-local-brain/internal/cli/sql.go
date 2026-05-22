// Hand-authored Phase 3 novel command. The framework's SQL command (when
// emitted) targets the offline-cache store; we want SELECT against the union
// of every namespace's memories table with an extra `namespace` column.

package cli

import (
	"fmt"
	"strings"

	"local-brain-pp-cli/internal/brain"

	"github.com/spf13/cobra"
)

func newSQLCmd(flags *rootFlags) *cobra.Command {
	var flagNamespace string

	cmd := &cobra.Command{
		Use:     "sql <query>",
		Short:   "Run a read-only SELECT statement against the union of all memories tables (namespace column appended)",
		Example: `  local-brain-pp-cli sql "SELECT namespace, type, COUNT(*) FROM memories GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10"`,
		Annotations: map[string]string{
			"pp:endpoint":   "sql.query",
			"pp:method":     "POST",
			"pp:path":       "/sql/query",
			"mcp:read-only": "true",
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return cmd.Help()
			}
			query := strings.TrimSpace(args[0])
			if !isSelectOnly(query) {
				return fmt.Errorf("only SELECT statements are allowed (got: %q)", firstWord(query))
			}
			if dryRunOK(flags) {
				return emitJSON(cmd.OutOrStdout(), map[string]any{"dry_run": true, "query": query, "namespace": flagNamespace}, flags)
			}
			ctx := cmd.Context()
			namespaces, err := resolveNamespacesForSQL(flagNamespace)
			if err != nil {
				return err
			}
			var rowsOut []map[string]any
			for _, ns := range namespaces {
				db, err := brain.OpenReadOnly(ctx, ns)
				if err != nil {
					continue
				}
				rows, err := db.QueryContext(ctx, query)
				if err != nil {
					_ = db.Close()
					return fmt.Errorf("query in %s: %w", ns, err)
				}
				cols, err := rows.Columns()
				if err != nil {
					_ = rows.Close()
					_ = db.Close()
					return err
				}
				for rows.Next() {
					vals := make([]any, len(cols))
					ptrs := make([]any, len(cols))
					for i := range vals {
						ptrs[i] = &vals[i]
					}
					if err := rows.Scan(ptrs...); err != nil {
						return err
					}
					m := map[string]any{"namespace": ns}
					for i, c := range cols {
						m[c] = unwrapBytes(vals[i])
					}
					rowsOut = append(rowsOut, m)
				}
				_ = rows.Close()
				_ = db.Close()
			}
			return emitJSON(cmd.OutOrStdout(), rowsOut, flags)
		},
	}
	cmd.Flags().StringVar(&flagNamespace, "namespace", "", "Restrict to a single namespace (default: every namespace, results tagged)")

	return cmd
}

func resolveNamespacesForSQL(sel string) ([]string, error) {
	all, err := brain.ListNamespaces()
	if err != nil {
		return nil, err
	}
	if sel == "" {
		return all, nil
	}
	for _, n := range all {
		if n == sel {
			return []string{n}, nil
		}
	}
	return nil, fmt.Errorf("namespace %q not found", sel)
}

func isSelectOnly(q string) bool {
	upper := strings.ToUpper(strings.TrimLeft(q, " \t\r\n("))
	return strings.HasPrefix(upper, "SELECT") || strings.HasPrefix(upper, "WITH")
}

func firstWord(q string) string {
	q = strings.TrimSpace(q)
	if i := strings.IndexAny(q, " \t\n\r("); i > 0 {
		return q[:i]
	}
	return q
}

func unwrapBytes(v any) any {
	if b, ok := v.([]byte); ok {
		return string(b)
	}
	return v
}
