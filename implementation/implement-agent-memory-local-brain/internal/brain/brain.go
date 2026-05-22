// Package brain provides direct SQLite access to ~/.local-brain/<namespace>/memories.db.
//
// This is the local-brain-cli equivalent of LocalBrainMCP/src/local_brain_mcp/server.py:
// same on-disk schema, same WAL journal mode, same FTS5 + sqlite-vec compatibility.
// The python MCP server and this CLI can run concurrently against the same database.
package brain

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

// MemoryTypes is the set of valid memory.type values, mirroring server.py.
var MemoryTypes = []string{"insight", "decision", "outcome", "action_item", "preference", "compiled"}

// Memory mirrors the columns of the memories table.
type Memory struct {
	ID        string  `json:"id"`
	Type      string  `json:"type"`
	Content   string  `json:"content"`
	Tags      string  `json:"tags"`
	Source    string  `json:"source"`
	Namespace string  `json:"namespace"`
	CreatedAt string  `json:"created_at"`
	Hash      string  `json:"hash"`
	// Search-result decorations (zero-valued in non-search contexts):
	MatchType string  `json:"match_type,omitempty"`
	Score     float64 `json:"score,omitempty"`
	Distance  float64 `json:"distance,omitempty"`
}

// BrainDir returns the absolute path to the local-brain root, defaulting to
// ~/.local-brain unless overridden by LOCAL_BRAIN_DIR.
func BrainDir() string {
	if v := os.Getenv("LOCAL_BRAIN_DIR"); v != "" {
		return v
	}
	home, err := os.UserHomeDir()
	if err != nil {
		// Fall back to current dir; the caller will get a clear "no such file" later.
		return ".local-brain"
	}
	return filepath.Join(home, ".local-brain")
}

// NamespaceDir returns ~/.local-brain/<namespace>/.
func NamespaceDir(namespace string) string {
	return filepath.Join(BrainDir(), namespace)
}

// DBPath returns the SQLite path for a namespace.
func DBPath(namespace string) string {
	return filepath.Join(NamespaceDir(namespace), "memories.db")
}

// MarkdownPath returns the markdown mirror path for a namespace.
func MarkdownPath(namespace string) string {
	return filepath.Join(NamespaceDir(namespace), "memories.md")
}

// HasNamespace reports whether the namespace's memories.db file exists.
func HasNamespace(namespace string) bool {
	_, err := os.Stat(DBPath(namespace))
	return err == nil
}

// Open opens (and creates if missing) the SQLite database for a namespace,
// applying the schema defined by LocalBrainMCP server.py:_get_db.
//
// WAL journal mode is set so the python MCP server, this CLI, and any
// concurrent readers/writers can co-exist. The vec0 virtual table is NOT
// created here — embeddings backfill happens through the vendored Python
// embedder script which holds the sqlite-vec extension and the process-level
// lock that prevents shadow-table races.
func Open(ctx context.Context, namespace string) (*sql.DB, error) {
	dir := NamespaceDir(namespace)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("creating namespace dir %s: %w", dir, err)
	}
	dbPath := DBPath(namespace)
	// file: URI lets us pass driver-level params if we ever need them; today
	// we just need the path to be unambiguous.
	dsn := "file:" + dbPath + "?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("opening %s: %w", dbPath, err)
	}
	if err := ensureSchema(ctx, db); err != nil {
		_ = db.Close()
		return nil, err
	}
	return db, nil
}

// OpenReadOnly opens the namespace database read-only. Returns a sql.ErrNoRows-shaped
// error if the namespace doesn't exist (caller decides whether to surface).
func OpenReadOnly(ctx context.Context, namespace string) (*sql.DB, error) {
	dbPath := DBPath(namespace)
	if _, err := os.Stat(dbPath); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("namespace %q not found at %s", namespace, dbPath)
		}
		return nil, err
	}
	dsn := "file:" + dbPath + "?mode=ro&_pragma=busy_timeout(5000)"
	return sql.Open("sqlite", dsn)
}

// ensureSchema creates the memories table, FTS5 virtual table, and sync triggers.
// Idempotent — safe to call on every Open.
func ensureSchema(ctx context.Context, db *sql.DB) error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS memories (
			id TEXT PRIMARY KEY,
			type TEXT NOT NULL,
			content TEXT NOT NULL,
			tags TEXT DEFAULT '',
			source TEXT DEFAULT '',
			created_at TEXT NOT NULL,
			hash TEXT NOT NULL
		)`,
		`CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
			id, content, tags, source, content=memories, content_rowid=rowid
		)`,
		`CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
			INSERT INTO memories_fts(rowid, id, content, tags, source)
			VALUES (new.rowid, new.id, new.content, new.tags, new.source);
		END`,
		`CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
			INSERT INTO memories_fts(memories_fts, rowid, id, content, tags, source)
			VALUES ('delete', old.rowid, old.id, old.content, old.tags, old.source);
		END`,
	}
	for _, s := range stmts {
		if _, err := db.ExecContext(ctx, s); err != nil {
			return fmt.Errorf("schema: %w", err)
		}
	}
	return nil
}

// ListNamespaces returns every namespace under ~/.local-brain/ that has a
// memories.db file, in lexicographic order. The namespace is the relative
// path from the brain root (e.g., "global", "accounts/proofpoint").
func ListNamespaces() ([]string, error) {
	root := BrainDir()
	if _, err := os.Stat(root); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	var out []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // skip unreadable paths
		}
		if info.IsDir() {
			return nil
		}
		if filepath.Base(path) != "memories.db" {
			return nil
		}
		rel, rerr := filepath.Rel(root, filepath.Dir(path))
		if rerr != nil {
			return nil
		}
		// On Windows the separator could be `\`; normalize to forward-slash so
		// downstream consumers (search, JSON output) see a stable shape.
		rel = filepath.ToSlash(rel)
		if rel == "." || rel == "" {
			rel = "global"
		}
		out = append(out, rel)
		return nil
	})
	if err != nil {
		return nil, err
	}
	sort.Strings(out)
	return out, nil
}

// GenerateID returns a unique memory ID matching the format used by server.py:
// "mem-YYYYMMDD-HHMMSS-<8 hex chars>".
func GenerateID() string {
	now := time.Now().UTC()
	ts := now.Format("20060102-150405")
	seed := fmt.Sprintf("%s-%d", ts, now.UnixNano())
	sum := sha256.Sum256([]byte(seed))
	return "mem-" + ts + "-" + hex.EncodeToString(sum[:])[:8]
}

// ContentHash mirrors server.py: hashlib.sha256(content).hexdigest()[:16].
func ContentHash(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])[:16]
}

// Save writes a memory and returns the new row's ID. The caller may pass an
// empty createdAt to use the current time. After insert, this function
// regenerates the markdown mirror so curators get an Obsidian-friendly view.
func Save(ctx context.Context, db *sql.DB, namespace string, m *Memory) (string, error) {
	if m.ID == "" {
		m.ID = GenerateID()
	}
	if m.Type == "" {
		m.Type = "insight"
	}
	if !validType(m.Type) {
		return "", fmt.Errorf("invalid type %q (allowed: %s)", m.Type, strings.Join(MemoryTypes, ", "))
	}
	if m.CreatedAt == "" {
		m.CreatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	}
	if m.Hash == "" {
		m.Hash = ContentHash(m.Content)
	}
	_, err := db.ExecContext(ctx,
		`INSERT INTO memories (id, type, content, tags, source, created_at, hash)
		 VALUES (?, ?, ?, ?, ?, ?, ?)`,
		m.ID, m.Type, m.Content, m.Tags, m.Source, m.CreatedAt, m.Hash,
	)
	if err != nil {
		return "", fmt.Errorf("insert: %w", err)
	}
	if err := WriteMarkdown(ctx, db, namespace); err != nil {
		// Markdown is a derived view; failing to write it shouldn't block the save.
		// Log via the returned error envelope so callers can surface it as a warning.
		return m.ID, fmt.Errorf("saved %s but markdown mirror failed: %w", m.ID, err)
	}
	return m.ID, nil
}

// validType reports whether t is one of the allowed memory types.
func validType(t string) bool {
	for _, v := range MemoryTypes {
		if v == t {
			return true
		}
	}
	return false
}

// Forget deletes one memory by ID. It also deletes the corresponding row in
// memories_vec when the table exists (via the AFTER DELETE trigger on
// memories_fts; the vec table doesn't have a trigger so we delete it
// explicitly when present).
func Forget(ctx context.Context, db *sql.DB, namespace, id string) (bool, error) {
	res, err := db.ExecContext(ctx, `DELETE FROM memories WHERE id = ?`, id)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return false, nil
	}
	// Best-effort embedding cleanup. The vec table only exists if a previous
	// embedder run created it — silently ignore errors.
	_, _ = db.ExecContext(ctx, `DELETE FROM memories_vec WHERE id = ?`, id)

	// Markdown mirror regen.
	_ = WriteMarkdown(ctx, db, namespace)
	return true, nil
}

// ForgetAcrossAll iterates namespaces and deletes the first match. Returns
// (namespace_where_found, deleted_bool, err).
func ForgetAcrossAll(ctx context.Context, id string) (string, bool, error) {
	namespaces, err := ListNamespaces()
	if err != nil {
		return "", false, err
	}
	for _, ns := range namespaces {
		db, err := Open(ctx, ns)
		if err != nil {
			continue
		}
		ok, err := Forget(ctx, db, ns, id)
		_ = db.Close()
		if err != nil {
			return ns, false, err
		}
		if ok {
			return ns, true, nil
		}
	}
	return "", false, nil
}

// Get returns one memory by ID (caller restricts namespace via openFn).
// Returns sql.ErrNoRows if not found.
func Get(ctx context.Context, db *sql.DB, id string) (*Memory, error) {
	row := db.QueryRowContext(ctx,
		`SELECT id, type, content, tags, source, created_at, hash FROM memories WHERE id = ?`, id)
	m := &Memory{}
	if err := row.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
		return nil, err
	}
	return m, nil
}

// GetAcrossAll searches every namespace for the ID. Returns the first match
// or sql.ErrNoRows if not found anywhere.
func GetAcrossAll(ctx context.Context, id string) (*Memory, error) {
	namespaces, err := ListNamespaces()
	if err != nil {
		return nil, err
	}
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		m, err := Get(ctx, db, id)
		_ = db.Close()
		if err == nil {
			m.Namespace = ns
			return m, nil
		}
	}
	return nil, sql.ErrNoRows
}

// ListOpts filters and limits a memory.list query.
type ListOpts struct {
	Namespace string
	Types     []string
	Tags      []string // AND-match: every tag must appear in the row's tags column
	Since     time.Time
	Before    time.Time
	Limit     int
}

// List returns memories from a namespace, ordered by created_at DESC.
func List(ctx context.Context, db *sql.DB, opts ListOpts) ([]Memory, error) {
	if opts.Limit <= 0 {
		opts.Limit = 50
	}
	q := `SELECT id, type, content, tags, source, created_at, hash FROM memories`
	var clauses []string
	var args []any
	if len(opts.Types) > 0 {
		ph := strings.TrimRight(strings.Repeat("?,", len(opts.Types)), ",")
		clauses = append(clauses, "type IN ("+ph+")")
		for _, t := range opts.Types {
			args = append(args, t)
		}
	}
	for _, tag := range opts.Tags {
		clauses = append(clauses, "tags LIKE ?")
		args = append(args, "%"+tag+"%")
	}
	if !opts.Since.IsZero() {
		clauses = append(clauses, "created_at >= ?")
		args = append(args, opts.Since.UTC().Format(time.RFC3339))
	}
	if !opts.Before.IsZero() {
		clauses = append(clauses, "created_at < ?")
		args = append(args, opts.Before.UTC().Format(time.RFC3339))
	}
	if len(clauses) > 0 {
		q += " WHERE " + strings.Join(clauses, " AND ")
	}
	q += " ORDER BY created_at DESC LIMIT ?"
	args = append(args, opts.Limit)

	rows, err := db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Memory
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
			return nil, err
		}
		m.Namespace = opts.Namespace
		out = append(out, m)
	}
	return out, rows.Err()
}

// ParseSince converts strings like "2h", "24h", "7d", or an ISO timestamp to a time.Time.
// Empty input returns zero-time.
func ParseSince(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, nil
	}
	// Duration shortcuts: 2h, 24h, 7d, 30m
	if d, err := parseDurationLoose(s); err == nil {
		return time.Now().UTC().Add(-d), nil
	}
	// Otherwise try a few absolute formats.
	formats := []string{
		time.RFC3339Nano, time.RFC3339,
		"2006-01-02 15:04:05", "2006-01-02",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("could not parse time %q (try 2h, 7d, or YYYY-MM-DD)", s)
}

// parseDurationLoose accepts standard time.ParseDuration syntax PLUS a "d"
// (days) shorthand, since Go's parser doesn't understand days.
func parseDurationLoose(s string) (time.Duration, error) {
	if strings.HasSuffix(s, "d") {
		var n int
		_, err := fmt.Sscanf(s, "%dd", &n)
		if err != nil {
			return 0, err
		}
		return time.Duration(n) * 24 * time.Hour, nil
	}
	return time.ParseDuration(s)
}

// SplitCSV splits a comma-separated string and trims/empty-filters the parts.
func SplitCSV(s string) []string {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

// RotateTagDelete removes any memories in this namespace whose tags column
// contains the given rotation marker. Used by `memory save --rotate-tag`.
// Returns the number of rows deleted.
func RotateTagDelete(ctx context.Context, db *sql.DB, marker string) (int, error) {
	if marker == "" {
		return 0, nil
	}
	res, err := db.ExecContext(ctx, `DELETE FROM memories WHERE tags LIKE ?`, "%"+marker+"%")
	if err != nil {
		return 0, err
	}
	n, _ := res.RowsAffected()
	return int(n), nil
}
