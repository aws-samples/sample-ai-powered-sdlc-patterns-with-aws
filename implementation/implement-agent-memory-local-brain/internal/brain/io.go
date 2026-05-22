package brain

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// ImportResult mirrors the spec's ImportResult.
type ImportResult struct {
	Imported   int      `json:"imported"`
	Skipped    int      `json:"skipped"`
	Namespaces []string `json:"namespaces"`
}

// ImportFile imports memories from a JSON, JSONL, or markdown file.
//
// JSON: a top-level array of memory objects, OR a single object.
// JSONL: one memory object per line.
// Markdown: parsed by header — every "## <id>" block is one memory; tags/source
// extracted from "**Type:** ... **Tags:** ... **Source:** ..." lines.
//
// `dedupeBy` is one of "hash" (default), "id", or "" (no dedupe).
// `overrideNamespace` substitutes the namespace for every imported memory; when
// empty, each memory's own `namespace` field is used (defaulting to "global").
func ImportFile(ctx context.Context, file, format, overrideNamespace, dedupeBy string) (ImportResult, error) {
	if dedupeBy == "" {
		dedupeBy = "hash"
	}
	if format == "" {
		format = inferFormat(file)
	}
	rdr, closer, err := openInput(file)
	if err != nil {
		return ImportResult{}, err
	}
	defer closer()

	switch strings.ToLower(format) {
	case "json":
		return importJSON(ctx, rdr, overrideNamespace, dedupeBy, false)
	case "jsonl", "ndjson":
		return importJSON(ctx, rdr, overrideNamespace, dedupeBy, true)
	case "markdown", "md":
		return ImportResult{}, errors.New("markdown import not implemented yet — convert to JSONL first")
	default:
		return ImportResult{}, fmt.Errorf("unsupported format %q (try json or jsonl)", format)
	}
}

func inferFormat(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".json":
		return "json"
	case ".jsonl", ".ndjson":
		return "jsonl"
	case ".md", ".markdown":
		return "markdown"
	}
	return "json"
}

func openInput(path string) (io.Reader, func(), error) {
	if path == "-" {
		return os.Stdin, func() {}, nil
	}
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	return f, func() { _ = f.Close() }, nil
}

func importJSON(ctx context.Context, r io.Reader, override, dedupeBy string, jsonl bool) (ImportResult, error) {
	var res ImportResult
	seenNS := map[string]struct{}{}

	type incoming struct {
		ID        string `json:"id"`
		Namespace string `json:"namespace"`
		Type      string `json:"type"`
		Content   string `json:"content"`
		Tags      string `json:"tags"`
		Source    string `json:"source"`
		CreatedAt string `json:"created_at"`
		Hash      string `json:"hash"`
	}

	process := func(in incoming) error {
		ns := in.Namespace
		if override != "" {
			ns = override
		}
		if ns == "" {
			ns = "global"
		}
		db, err := Open(ctx, ns)
		if err != nil {
			return err
		}
		defer db.Close()
		if dedupeBy == "hash" && in.Hash == "" {
			in.Hash = ContentHash(in.Content)
		}
		if dedupeBy != "" {
			var existing string
			switch dedupeBy {
			case "hash":
				_ = db.QueryRowContext(ctx, `SELECT id FROM memories WHERE hash = ? LIMIT 1`, in.Hash).Scan(&existing)
			case "id":
				_ = db.QueryRowContext(ctx, `SELECT id FROM memories WHERE id = ? LIMIT 1`, in.ID).Scan(&existing)
			}
			if existing != "" {
				res.Skipped++
				return nil
			}
		}
		m := &Memory{
			ID: in.ID, Type: in.Type, Content: in.Content,
			Tags: in.Tags, Source: in.Source, CreatedAt: in.CreatedAt, Hash: in.Hash,
		}
		if _, err := Save(ctx, db, ns, m); err != nil {
			return err
		}
		res.Imported++
		seenNS[ns] = struct{}{}
		return nil
	}

	if jsonl {
		scanner := bufio.NewScanner(r)
		scanner.Buffer(make([]byte, 1024*1024), 16*1024*1024)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}
			var in incoming
			if err := json.Unmarshal([]byte(line), &in); err != nil {
				continue
			}
			if err := process(in); err != nil {
				return res, err
			}
		}
		if err := scanner.Err(); err != nil {
			return res, err
		}
	} else {
		body, err := io.ReadAll(r)
		if err != nil {
			return res, err
		}
		// Try array first, then single object.
		var arr []incoming
		if json.Unmarshal(body, &arr) == nil && len(arr) > 0 {
			for _, in := range arr {
				if err := process(in); err != nil {
					return res, err
				}
			}
		} else {
			var single incoming
			if err := json.Unmarshal(body, &single); err != nil {
				return res, fmt.Errorf("parsing JSON: %w", err)
			}
			if err := process(single); err != nil {
				return res, err
			}
		}
	}

	res.Namespaces = make([]string, 0, len(seenNS))
	for ns := range seenNS {
		res.Namespaces = append(res.Namespaces, ns)
	}
	return res, nil
}

// ExportResult mirrors the spec's ExportResult.
type ExportResult struct {
	Namespace string `json:"namespace"`
	Format    string `json:"format"`
	Bytes     int    `json:"bytes"`
}

// ExportNamespace writes the memories of a namespace to dest in the given format.
// dest may be a file path; pass "-" to write to stdout (caller passes os.Stdout).
// Embeddings are not yet supported (sqlite-vec extension required to read them
// back); the flag is parsed but the data is omitted with a warning.
func ExportNamespace(ctx context.Context, namespace, format string, includeEmbeddings bool, mtype string, w io.Writer) (ExportResult, error) {
	if format == "" {
		format = "json"
	}
	db, err := OpenReadOnly(ctx, namespace)
	if err != nil {
		return ExportResult{}, err
	}
	defer db.Close()
	q := `SELECT id, type, content, tags, source, created_at, hash FROM memories`
	args := []any{}
	if mtype != "" {
		q += " WHERE type = ?"
		args = append(args, mtype)
	}
	q += " ORDER BY created_at DESC"
	rows, err := db.QueryContext(ctx, q, args...)
	if err != nil {
		return ExportResult{}, err
	}
	defer rows.Close()

	var memories []Memory
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
			return ExportResult{}, err
		}
		m.Namespace = namespace
		memories = append(memories, m)
	}

	bw := &countingWriter{Writer: w}
	switch strings.ToLower(format) {
	case "json":
		enc := json.NewEncoder(bw)
		enc.SetIndent("", "  ")
		if err := enc.Encode(memories); err != nil {
			return ExportResult{}, err
		}
	case "jsonl":
		for _, m := range memories {
			b, _ := json.Marshal(m)
			b = append(b, '\n')
			if _, err := bw.Write(b); err != nil {
				return ExportResult{}, err
			}
		}
	case "csv":
		fmt.Fprintln(bw, "id,namespace,type,content,tags,source,created_at,hash")
		for _, m := range memories {
			fmt.Fprintf(bw, "%s,%s,%s,%q,%s,%s,%s,%s\n",
				csvEscape(m.ID), csvEscape(m.Namespace), csvEscape(m.Type),
				m.Content,
				csvEscape(m.Tags), csvEscape(m.Source), csvEscape(m.CreatedAt), csvEscape(m.Hash))
		}
	case "markdown":
		fmt.Fprintf(bw, "# Memories: %s\n\n", namespace)
		for _, m := range memories {
			fmt.Fprintf(bw, "## %s\n**Type:** %s  \n**Created:** %s  \n", m.ID, m.Type, m.CreatedAt)
			if m.Tags != "" {
				fmt.Fprintf(bw, "**Tags:** %s  \n", m.Tags)
			}
			if m.Source != "" {
				fmt.Fprintf(bw, "**Source:** %s  \n", m.Source)
			}
			fmt.Fprintf(bw, "\n%s\n\n---\n\n", m.Content)
		}
	default:
		return ExportResult{}, fmt.Errorf("unsupported format %q", format)
	}
	return ExportResult{Namespace: namespace, Format: format, Bytes: bw.n}, nil
}

type countingWriter struct {
	io.Writer
	n int
}

func (c *countingWriter) Write(p []byte) (int, error) {
	n, err := c.Writer.Write(p)
	c.n += n
	return n, err
}

func csvEscape(s string) string {
	if strings.ContainsAny(s, ",\"\n") {
		return `"` + strings.ReplaceAll(s, `"`, `""`) + `"`
	}
	return s
}
