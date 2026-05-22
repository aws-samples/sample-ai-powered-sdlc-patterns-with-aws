package brain

import (
	"archive/tar"
	"compress/gzip"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// NamespaceCount reports the row count for one namespace.
type NamespaceCount struct {
	Namespace string `json:"namespace"`
	Count     int    `json:"count"`
}

// NamespaceList returns counts for every namespace, optionally filtered by a
// simple prefix glob (`accounts/*`). Empty filter returns everything.
func NamespaceList(ctx context.Context, filter string) ([]NamespaceCount, error) {
	all, err := ListNamespaces()
	if err != nil {
		return nil, err
	}
	out := make([]NamespaceCount, 0, len(all))
	prefix := strings.TrimSuffix(filter, "*")
	for _, ns := range all {
		if filter != "" && !strings.HasPrefix(ns, prefix) {
			continue
		}
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		var n int
		_ = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM memories`).Scan(&n)
		_ = db.Close()
		out = append(out, NamespaceCount{Namespace: ns, Count: n})
	}
	return out, nil
}

// Rename renames a namespace by moving its directory. Returns the number of
// memories moved (i.e., the row count after rename).
func Rename(ctx context.Context, from, to string) (int, error) {
	if from == "" || to == "" {
		return 0, errors.New("from and to are required")
	}
	src := NamespaceDir(from)
	dst := NamespaceDir(to)
	if _, err := os.Stat(src); err != nil {
		return 0, fmt.Errorf("source %q not found", from)
	}
	if _, err := os.Stat(dst); err == nil {
		return 0, fmt.Errorf("target %q already exists", to)
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return 0, err
	}
	if err := os.Rename(src, dst); err != nil {
		return 0, err
	}
	// Regenerate markdown so the header reads the new namespace name.
	db, err := Open(ctx, to)
	if err != nil {
		return 0, err
	}
	defer db.Close()
	var n int
	_ = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM memories`).Scan(&n)
	_ = WriteMarkdown(ctx, db, to)
	return n, nil
}

// Move relocates memories of a given type (or all when type is empty) from one
// namespace to another. Useful when refactoring tag taxonomies.
func Move(ctx context.Context, from, to, mtype string) (int, error) {
	if from == "" || to == "" {
		return 0, errors.New("from and to are required")
	}
	srcDB, err := Open(ctx, from)
	if err != nil {
		return 0, err
	}
	defer srcDB.Close()
	dstDB, err := Open(ctx, to)
	if err != nil {
		return 0, err
	}
	defer dstDB.Close()

	q := `SELECT id, type, content, tags, source, created_at, hash FROM memories`
	args := []any{}
	if mtype != "" {
		q += " WHERE type = ?"
		args = append(args, mtype)
	}
	rows, err := srcDB.QueryContext(ctx, q, args...)
	if err != nil {
		return 0, err
	}
	defer rows.Close()

	moved := 0
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
			return moved, err
		}
		if _, err := dstDB.ExecContext(ctx,
			`INSERT INTO memories (id, type, content, tags, source, created_at, hash) VALUES (?, ?, ?, ?, ?, ?, ?)
			 ON CONFLICT(id) DO NOTHING`,
			m.ID, m.Type, m.Content, m.Tags, m.Source, m.CreatedAt, m.Hash); err != nil {
			return moved, err
		}
		if _, err := srcDB.ExecContext(ctx, `DELETE FROM memories WHERE id = ?`, m.ID); err != nil {
			return moved, err
		}
		moved++
	}
	if err := rows.Err(); err != nil {
		return moved, err
	}
	_ = WriteMarkdown(ctx, srcDB, from)
	_ = WriteMarkdown(ctx, dstDB, to)
	return moved, nil
}

// DeleteNamespace removes the namespace directory and everything inside.
// Caller is expected to have asked the user for explicit confirmation.
func DeleteNamespace(namespace string) error {
	if namespace == "" {
		return errors.New("namespace is required")
	}
	dir := NamespaceDir(namespace)
	if _, err := os.Stat(dir); err != nil {
		return fmt.Errorf("namespace %q not found", namespace)
	}
	return os.RemoveAll(dir)
}

// VacuumOne issues a SQLite VACUUM against one namespace's database, returning
// the bytes saved (pre - post).
func VacuumOne(ctx context.Context, namespace string) (int64, error) {
	dbPath := DBPath(namespace)
	stat, err := os.Stat(dbPath)
	if err != nil {
		return 0, err
	}
	pre := stat.Size()
	db, err := Open(ctx, namespace)
	if err != nil {
		return 0, err
	}
	if _, err := db.ExecContext(ctx, `VACUUM`); err != nil {
		_ = db.Close()
		return 0, err
	}
	_ = db.Close()
	stat2, err := os.Stat(dbPath)
	if err != nil {
		return 0, err
	}
	return pre - stat2.Size(), nil
}

// VacuumAll vacuums every namespace; returns total bytes saved.
func VacuumAll(ctx context.Context) (int64, []NamespaceCount, error) {
	all, err := ListNamespaces()
	if err != nil {
		return 0, nil, err
	}
	var total int64
	var perNS []NamespaceCount
	for _, ns := range all {
		saved, err := VacuumOne(ctx, ns)
		if err != nil {
			continue
		}
		total += saved
		perNS = append(perNS, NamespaceCount{Namespace: ns, Count: int(saved)})
	}
	return total, perNS, nil
}

// Backup writes a tar.gz of one namespace (or all when namespace == "") to dest.
// dest may be a directory (in which case a default filename is generated) or
// an explicit .tar.gz path.
func Backup(ctx context.Context, namespace, dest string, all bool) (string, []string, error) {
	var namespaces []string
	if all || namespace == "" {
		ns, err := ListNamespaces()
		if err != nil {
			return "", nil, err
		}
		namespaces = ns
	} else {
		namespaces = []string{namespace}
	}
	if dest == "" {
		dest = filepath.Join(os.TempDir(), fmt.Sprintf("local-brain-backup-%s.tar.gz", time.Now().UTC().Format("20060102-150405")))
	}
	if fi, err := os.Stat(dest); err == nil && fi.IsDir() {
		dest = filepath.Join(dest, fmt.Sprintf("local-brain-backup-%s.tar.gz", time.Now().UTC().Format("20060102-150405")))
	}
	f, err := os.Create(dest)
	if err != nil {
		return "", nil, err
	}
	defer f.Close()
	gz := gzip.NewWriter(f)
	defer gz.Close()
	tw := tar.NewWriter(gz)
	defer tw.Close()

	for _, ns := range namespaces {
		dir := NamespaceDir(ns)
		err := filepath.Walk(dir, func(path string, info os.FileInfo, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if info.IsDir() {
				return nil
			}
			rel, _ := filepath.Rel(BrainDir(), path)
			hdr, err := tar.FileInfoHeader(info, "")
			if err != nil {
				return err
			}
			hdr.Name = filepath.ToSlash(rel)
			if err := tw.WriteHeader(hdr); err != nil {
				return err
			}
			r, err := os.Open(path)
			if err != nil {
				return err
			}
			_, err = io.Copy(tw, r)
			_ = r.Close()
			return err
		})
		if err != nil {
			return dest, namespaces, err
		}
	}
	return dest, namespaces, nil
}

// Restore extracts a tar.gz archive into the brain dir. When renameTo is set,
// every entry under the original namespace directory is rewritten to renameTo.
// merge=true accepts pre-existing namespace dirs; merge=false rejects them.
func Restore(ctx context.Context, archive, renameTo string, merge bool) (int, string, error) {
	f, err := os.Open(archive)
	if err != nil {
		return 0, "", err
	}
	defer f.Close()
	gz, err := gzip.NewReader(f)
	if err != nil {
		return 0, "", err
	}
	defer gz.Close()
	tr := tar.NewReader(gz)

	root := BrainDir()
	if err := os.MkdirAll(root, 0o755); err != nil {
		return 0, "", err
	}

	restored := 0
	originalNS := ""
	for {
		hdr, err := tr.Next()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return restored, originalNS, err
		}
		if hdr.FileInfo().IsDir() {
			continue
		}
		// Header names look like "<ns>/memories.db" or "<ns>/sub/...".
		// Capture the original NS from the first segment.
		parts := strings.SplitN(hdr.Name, "/", 2)
		if originalNS == "" && len(parts) > 1 {
			originalNS = parts[0]
		}
		target := filepath.Join(root, hdr.Name)
		if renameTo != "" && len(parts) > 1 {
			target = filepath.Join(root, renameTo, parts[1])
		}
		if !merge {
			if _, err := os.Stat(target); err == nil {
				return restored, originalNS, fmt.Errorf("%s already exists; pass --merge to overwrite", target)
			}
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return restored, originalNS, err
		}
		out, err := os.Create(target)
		if err != nil {
			return restored, originalNS, err
		}
		if _, err := io.Copy(out, tr); err != nil {
			_ = out.Close()
			return restored, originalNS, err
		}
		_ = out.Close()
		restored++
	}
	return restored, originalNS, nil
}
