package brain

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"strings"
	"time"
)

// WriteMarkdown regenerates ~/.local-brain/<namespace>/memories.md from the
// SQLite database. Mirrors LocalBrainMCP server.py:_update_markdown so the
// human-readable view stays Obsidian-compatible regardless of which client
// (python MCP, this CLI) wrote the row.
func WriteMarkdown(ctx context.Context, db *sql.DB, namespace string) error {
	rows, err := db.QueryContext(ctx,
		`SELECT id, type, content, tags, source, created_at FROM memories ORDER BY created_at DESC`)
	if err != nil {
		return err
	}
	defer rows.Close()

	var b strings.Builder
	fmt.Fprintf(&b, "# Memories: %s\n\n", namespace)
	fmt.Fprintf(&b, "_Updated: %s_\n\n", time.Now().UTC().Format(time.RFC3339))
	count := 0
	var entries []string
	for rows.Next() {
		var id, mtype, content, tags, source, createdAt string
		if err := rows.Scan(&id, &mtype, &content, &tags, &source, &createdAt); err != nil {
			return err
		}
		var e strings.Builder
		fmt.Fprintf(&e, "## %s\n", id)
		fmt.Fprintf(&e, "**Type:** %s  \n", mtype)
		fmt.Fprintf(&e, "**Created:** %s  \n", createdAt)
		if tags != "" {
			fmt.Fprintf(&e, "**Tags:** %s  \n", tags)
		}
		if source != "" {
			fmt.Fprintf(&e, "**Source:** %s  \n", source)
		}
		fmt.Fprintf(&e, "\n%s\n\n---\n", content)
		entries = append(entries, e.String())
		count++
	}
	if err := rows.Err(); err != nil {
		return err
	}
	fmt.Fprintf(&b, "_%d memories_\n\n---\n", count)
	for _, e := range entries {
		b.WriteString(e + "\n")
	}
	return os.WriteFile(MarkdownPath(namespace), []byte(b.String()), 0o644)
}
