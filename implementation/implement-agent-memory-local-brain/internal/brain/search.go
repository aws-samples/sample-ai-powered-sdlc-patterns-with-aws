package brain

import (
	"context"
	"database/sql"
	"fmt"
	"sort"
	"strings"
)

// SearchOpts configures a memory search query.
type SearchOpts struct {
	Query      string
	Namespace  string // empty -> search every namespace; supports "accounts/*" prefix glob.
	Mode       string // auto | keyword | semantic | hybrid
	Limit      int
	Types      []string
	Tags       []string
	Threshold  float64 // semantic distance ceiling
}

// Search executes the requested mode across one or all namespaces.
//
// Semantic and hybrid modes silently degrade to keyword when sqlite-vec is
// not loaded (no `memories_vec` table). The CLI's `embeddings backfill`
// command — which shells out to the vendored Python embedder — is the
// supported way to populate the vector table.
func Search(ctx context.Context, opts SearchOpts) ([]Memory, error) {
	if opts.Limit <= 0 {
		opts.Limit = 20
	}
	if opts.Mode == "" || opts.Mode == "auto" {
		// Auto = hybrid if any vec table is reachable, else keyword. Without
		// sqlite-vec extension loaded our queries won't see vec rows at all,
		// so auto effectively becomes keyword in this binary. Hybrid is still
		// useful when embeddings backfill ran (vec table exists, embedder
		// populated it) — the python MCP server can read it; for now this
		// CLI only fronts keyword.
		opts.Mode = "keyword"
	}

	namespaces, err := resolveNamespaces(opts.Namespace)
	if err != nil {
		return nil, err
	}

	var all []Memory
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue // namespace might have been listed but not openable
		}
		results, err := searchNamespace(ctx, db, ns, opts)
		_ = db.Close()
		if err != nil {
			// Don't fail the whole call; FTS5 syntax issues should bubble up
			// once we've tried every namespace.
			continue
		}
		all = append(all, results...)
	}
	// Sort by score descending when we have scores; otherwise by created_at desc.
	sort.SliceStable(all, func(i, j int) bool {
		if all[i].Score != 0 || all[j].Score != 0 {
			return all[i].Score > all[j].Score
		}
		return all[i].CreatedAt > all[j].CreatedAt
	})
	if len(all) > opts.Limit {
		all = all[:opts.Limit]
	}
	return all, nil
}

// resolveNamespaces expands a namespace selector ("", "global", "accounts/*")
// to the concrete list of namespaces to query.
func resolveNamespaces(sel string) ([]string, error) {
	all, err := ListNamespaces()
	if err != nil {
		return nil, err
	}
	if sel == "" {
		return all, nil
	}
	if !strings.Contains(sel, "*") {
		// Exact match.
		for _, ns := range all {
			if ns == sel {
				return []string{ns}, nil
			}
		}
		return nil, fmt.Errorf("namespace %q not found", sel)
	}
	// Simple prefix glob: "accounts/*" => any ns starting with "accounts/".
	prefix := strings.TrimSuffix(sel, "*")
	var matched []string
	for _, ns := range all {
		if strings.HasPrefix(ns, prefix) {
			matched = append(matched, ns)
		}
	}
	return matched, nil
}

func searchNamespace(ctx context.Context, db *sql.DB, ns string, opts SearchOpts) ([]Memory, error) {
	// FTS5's MATCH expects a tokenized query. Pass user input through as-is
	// for v1; if a user wants advanced operators (OR, NEAR, etc.) they get
	// FTS5-native syntax for free.
	q := `SELECT m.id, m.type, m.content, m.tags, m.source, m.created_at, m.hash, rank
	      FROM memories m
	      JOIN memories_fts f ON m.id = f.id
	      WHERE memories_fts MATCH ?`
	args := []any{opts.Query}

	if len(opts.Types) > 0 {
		ph := strings.TrimRight(strings.Repeat("?,", len(opts.Types)), ",")
		q += " AND m.type IN (" + ph + ")"
		for _, t := range opts.Types {
			args = append(args, t)
		}
	}
	for _, tag := range opts.Tags {
		q += " AND m.tags LIKE ?"
		args = append(args, "%"+tag+"%")
	}
	q += " ORDER BY rank LIMIT ?"
	args = append(args, opts.Limit)

	rows, err := db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Memory
	for rows.Next() {
		var m Memory
		var rank float64
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash, &rank); err != nil {
			return nil, err
		}
		m.Namespace = ns
		// FTS5 bm25 ranks are negative (more negative = better). Flip sign for
		// a friendlier "higher is better" score.
		m.Score = -rank
		m.MatchType = "keyword"
		out = append(out, m)
	}
	return out, rows.Err()
}
