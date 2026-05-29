package brain

import (
	"context"
	"database/sql"
	"sort"
	"time"
)

// StaleAction describes one overdue action_item memory.
type StaleAction struct {
	ID        string `json:"id"`
	Namespace string `json:"namespace"`
	Type      string `json:"type"`
	Content   string `json:"content"`
	CreatedAt string `json:"created_at"`
	AgeDays   int    `json:"age_days"`
}

// NamespaceStats mirrors LocalBrainMCP server.py:tool_memory_stats's per-namespace
// summary, with one extra field: OldestUnembedded (the date of the oldest row
// missing an embedding, when sqlite-vec data is reachable).
type NamespaceStats struct {
	Namespace          string         `json:"namespace"`
	Total              int            `json:"total"`
	AtomicCount        int            `json:"atomic_count"`
	CompiledCount      int            `json:"compiled_count"`
	ByType             map[string]int `json:"by_type"`
	Oldest             string         `json:"oldest"`
	Newest             string         `json:"newest"`
	LastCompiled       string         `json:"last_compiled"`
	StaleActionItems   []StaleAction  `json:"stale_action_items"`
	NeedsCompilation   bool           `json:"needs_compilation"`
	UnembeddedCount    int            `json:"unembedded_count"`
	OldestUnembedded   string         `json:"oldest_unembedded,omitempty"`
}

// Stats returns NamespaceStats for one or many namespaces. If selector is empty,
// every namespace under ~/.local-brain/ is summarized.
func Stats(ctx context.Context, selector string, staleDays int) ([]NamespaceStats, error) {
	if staleDays <= 0 {
		staleDays = 14
	}
	namespaces, err := resolveNamespaces(selector)
	if err != nil {
		return nil, err
	}
	var out []NamespaceStats
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		s, err := statsForNamespace(ctx, db, ns, staleDays)
		_ = db.Close()
		if err != nil {
			continue
		}
		out = append(out, s)
	}
	return out, nil
}

func statsForNamespace(ctx context.Context, db *sql.DB, ns string, staleDays int) (NamespaceStats, error) {
	s := NamespaceStats{Namespace: ns, ByType: map[string]int{}}

	// Counts by type.
	rows, err := db.QueryContext(ctx, `SELECT type, COUNT(*) FROM memories GROUP BY type`)
	if err != nil {
		return s, err
	}
	for rows.Next() {
		var t string
		var n int
		if err := rows.Scan(&t, &n); err != nil {
			rows.Close()
			return s, err
		}
		s.ByType[t] = n
		s.Total += n
	}
	rows.Close()
	s.CompiledCount = s.ByType["compiled"]
	s.AtomicCount = s.Total - s.CompiledCount

	// Date range.
	_ = db.QueryRowContext(ctx, `SELECT MIN(created_at), MAX(created_at) FROM memories`).Scan(nullableScan{&s.Oldest}, nullableScan{&s.Newest})
	_ = db.QueryRowContext(ctx, `SELECT MAX(created_at) FROM memories WHERE type='compiled'`).Scan(nullableScan{&s.LastCompiled})

	// Stale action items.
	cutoff := time.Now().UTC().AddDate(0, 0, -staleDays)
	rows2, err := db.QueryContext(ctx,
		`SELECT id, content, created_at FROM memories WHERE type='action_item' AND created_at < ? ORDER BY created_at ASC`,
		cutoff.Format(time.RFC3339),
	)
	if err == nil {
		for rows2.Next() {
			var id, content, createdAt string
			if err := rows2.Scan(&id, &content, &createdAt); err != nil {
				continue
			}
			t, perr := time.Parse(time.RFC3339Nano, createdAt)
			if perr != nil {
				t, _ = time.Parse(time.RFC3339, createdAt)
			}
			age := int(time.Since(t).Hours() / 24)
			short := content
			if len(short) > 200 {
				short = short[:200]
			}
			s.StaleActionItems = append(s.StaleActionItems, StaleAction{
				ID:        id,
				Namespace: ns,
				Type:      "action_item",
				Content:   short,
				CreatedAt: createdAt,
				AgeDays:   age,
			})
		}
		rows2.Close()
	}

	// needs_compilation: same heuristic as server.py.
	if s.AtomicCount >= 10 {
		if s.LastCompiled == "" || s.LastCompiled < s.Newest {
			s.NeedsCompilation = true
		}
	}

	// Unembedded count: requires the vec table to exist. If it doesn't, all
	// memories are "unembedded" by definition.
	var hasVec bool
	_ = db.QueryRowContext(ctx,
		`SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories_vec' LIMIT 1`).Scan(&hasVec)
	if hasVec {
		_ = db.QueryRowContext(ctx,
			`SELECT COUNT(*) FROM memories m WHERE m.id NOT IN (SELECT id FROM memories_vec)`).
			Scan(&s.UnembeddedCount)
		_ = db.QueryRowContext(ctx,
			`SELECT MIN(created_at) FROM memories m WHERE m.id NOT IN (SELECT id FROM memories_vec)`).
			Scan(nullableScan{&s.OldestUnembedded})
	} else {
		s.UnembeddedCount = s.Total
	}

	return s, nil
}

// nullableScan absorbs SQL NULLs into empty strings without forcing the caller
// to thread sql.NullString through every variable.
type nullableScan struct{ Dest *string }

func (n nullableScan) Scan(src any) error {
	if src == nil {
		*n.Dest = ""
		return nil
	}
	switch v := src.(type) {
	case string:
		*n.Dest = v
	case []byte:
		*n.Dest = string(v)
	}
	return nil
}

// Stale returns action_item-typed memories older than staleDays, across the
// requested namespaces, ordered oldest first.
func Stale(ctx context.Context, namespaceSelector, mtype string, staleDays, limit int) ([]StaleAction, error) {
	if staleDays <= 0 {
		staleDays = 14
	}
	if limit <= 0 {
		limit = 100
	}
	if mtype == "" {
		mtype = "action_item"
	}
	stats, err := Stats(ctx, namespaceSelector, staleDays)
	if err != nil {
		return nil, err
	}
	var all []StaleAction
	for _, s := range stats {
		if mtype == "action_item" {
			all = append(all, s.StaleActionItems...)
			continue
		}
		// For other types, we re-query directly; staleness logic is simple enough.
		db, err := OpenReadOnly(ctx, s.Namespace)
		if err != nil {
			continue
		}
		cutoff := time.Now().UTC().AddDate(0, 0, -staleDays).Format(time.RFC3339)
		rows, err := db.QueryContext(ctx,
			`SELECT id, content, created_at FROM memories WHERE type=? AND created_at < ? ORDER BY created_at ASC`,
			mtype, cutoff,
		)
		if err == nil {
			for rows.Next() {
				var id, content, createdAt string
				if err := rows.Scan(&id, &content, &createdAt); err != nil {
					continue
				}
				t, _ := time.Parse(time.RFC3339, createdAt)
				age := int(time.Since(t).Hours() / 24)
				short := content
				if len(short) > 200 {
					short = short[:200]
				}
				all = append(all, StaleAction{
					ID: id, Namespace: s.Namespace, Type: mtype,
					Content: short, CreatedAt: createdAt, AgeDays: age,
				})
			}
			rows.Close()
		}
		_ = db.Close()
	}
	sort.Slice(all, func(i, j int) bool { return all[i].CreatedAt < all[j].CreatedAt })
	if len(all) > limit {
		all = all[:limit]
	}
	return all, nil
}

// TagPattern reports a tag that appears across multiple namespaces.
type TagPattern struct {
	Tag        string   `json:"tag"`
	Namespaces []string `json:"namespaces"`
	Count      int      `json:"count"`
}

// Patterns identifies tags appearing in >= minNamespaces distinct namespaces.
// Mirrors the linter's heart: every tag occurrence is bucketed by its
// containing namespace; tags shared widely are surfaced. Excludes meta-tags
// like "compiled" and "auto-generated" by default.
func Patterns(ctx context.Context, minNamespaces, limit int, exclude []string) ([]TagPattern, error) {
	if minNamespaces <= 0 {
		minNamespaces = 3
	}
	if limit <= 0 {
		limit = 20
	}
	excludeSet := map[string]struct{}{
		"compiled": {}, "auto-generated": {},
	}
	for _, e := range exclude {
		excludeSet[e] = struct{}{}
	}

	tagToNs := map[string]map[string]struct{}{}
	namespaces, err := ListNamespaces()
	if err != nil {
		return nil, err
	}
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		rows, err := db.QueryContext(ctx, `SELECT tags FROM memories WHERE tags != ''`)
		if err == nil {
			for rows.Next() {
				var tags string
				if err := rows.Scan(&tags); err != nil {
					continue
				}
				for _, t := range SplitCSV(tags) {
					if _, skip := excludeSet[t]; skip {
						continue
					}
					if tagToNs[t] == nil {
						tagToNs[t] = map[string]struct{}{}
					}
					tagToNs[t][ns] = struct{}{}
				}
			}
			rows.Close()
		}
		_ = db.Close()
	}

	var out []TagPattern
	for tag, nsSet := range tagToNs {
		if len(nsSet) < minNamespaces {
			continue
		}
		nss := make([]string, 0, len(nsSet))
		for ns := range nsSet {
			nss = append(nss, ns)
		}
		sort.Strings(nss)
		out = append(out, TagPattern{Tag: tag, Namespaces: nss, Count: len(nss)})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].Tag < out[j].Tag
	})
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

// DupGroup describes a set of memories that share the same content hash.
type DupGroup struct {
	Hash    string   `json:"hash"`
	Members []DupMember `json:"members"`
	Count   int      `json:"count"`
}

// DupMember locates one row in a duplicate group.
type DupMember struct {
	ID        string `json:"id"`
	Namespace string `json:"namespace"`
	CreatedAt string `json:"created_at"`
}

// Dedupe finds duplicate memories by content hash. When apply is true, the
// caller's preferred winner (oldest) is kept and the rest are deleted.
func Dedupe(ctx context.Context, namespaceSelector string, apply bool) ([]DupGroup, error) {
	namespaces, err := resolveNamespaces(namespaceSelector)
	if err != nil {
		return nil, err
	}
	hashToMembers := map[string][]DupMember{}
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		rows, err := db.QueryContext(ctx, `SELECT id, hash, created_at FROM memories WHERE hash != ''`)
		if err == nil {
			for rows.Next() {
				var id, h, ca string
				if err := rows.Scan(&id, &h, &ca); err != nil {
					continue
				}
				hashToMembers[h] = append(hashToMembers[h], DupMember{ID: id, Namespace: ns, CreatedAt: ca})
			}
			rows.Close()
		}
		_ = db.Close()
	}
	var groups []DupGroup
	for h, members := range hashToMembers {
		if len(members) < 2 {
			continue
		}
		sort.Slice(members, func(i, j int) bool { return members[i].CreatedAt < members[j].CreatedAt })
		groups = append(groups, DupGroup{Hash: h, Members: members, Count: len(members)})
	}
	sort.Slice(groups, func(i, j int) bool { return groups[i].Count > groups[j].Count })

	if apply {
		// Keep the first (oldest) member, forget the rest, in their respective namespaces.
		for _, g := range groups {
			for _, m := range g.Members[1:] {
				db, err := Open(ctx, m.Namespace)
				if err != nil {
					continue
				}
				_, _ = Forget(ctx, db, m.Namespace, m.ID)
				_ = db.Close()
			}
		}
	}
	return groups, nil
}

// Bisect returns memories within `window` time before the compiled memory's
// created_at, scoped to the same namespace. This is the source-atom inference
// for compiled narratives.
func Bisect(ctx context.Context, compiledID, window string) ([]Memory, string, time.Time, error) {
	target, err := GetAcrossAll(ctx, compiledID)
	if err != nil {
		return nil, "", time.Time{}, err
	}
	if window == "" {
		window = "7d"
	}
	dur, err := parseDurationLoose(window)
	if err != nil {
		return nil, target.Namespace, time.Time{}, err
	}
	end, err := time.Parse(time.RFC3339Nano, target.CreatedAt)
	if err != nil {
		end, _ = time.Parse(time.RFC3339, target.CreatedAt)
	}
	start := end.Add(-dur)

	db, err := OpenReadOnly(ctx, target.Namespace)
	if err != nil {
		return nil, target.Namespace, end, err
	}
	defer db.Close()
	rows, err := db.QueryContext(ctx,
		`SELECT id, type, content, tags, source, created_at, hash
		   FROM memories
		  WHERE type != 'compiled'
		    AND created_at >= ?
		    AND created_at < ?
		  ORDER BY created_at ASC`,
		start.Format(time.RFC3339), end.Format(time.RFC3339),
	)
	if err != nil {
		return nil, target.Namespace, end, err
	}
	defer rows.Close()
	var out []Memory
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
			return nil, target.Namespace, end, err
		}
		m.Namespace = target.Namespace
		out = append(out, m)
	}
	return out, target.Namespace, end, rows.Err()
}

// NamespaceDiff captures what changed in one namespace since `since`.
type NamespaceDiff struct {
	Namespace    string         `json:"namespace"`
	Window       string         `json:"window"`
	Added        int            `json:"added"`
	ByType       map[string]int `json:"by_type"`
	NewMemories  []Memory       `json:"new_memories"`
}

// Diff computes a namespace's add-only diff over the given window.
func Diff(ctx context.Context, namespace, since string) (NamespaceDiff, error) {
	d := NamespaceDiff{Namespace: namespace, Window: since, ByType: map[string]int{}}
	cutoff, err := ParseSince(since)
	if err != nil {
		return d, err
	}
	if cutoff.IsZero() {
		cutoff = time.Now().UTC().Add(-7 * 24 * time.Hour)
		d.Window = "7d"
	}
	db, err := OpenReadOnly(ctx, namespace)
	if err != nil {
		return d, err
	}
	defer db.Close()
	rows, err := db.QueryContext(ctx,
		`SELECT id, type, content, tags, source, created_at, hash
		   FROM memories
		  WHERE created_at >= ?
		  ORDER BY created_at DESC`,
		cutoff.Format(time.RFC3339),
	)
	if err != nil {
		return d, err
	}
	defer rows.Close()
	for rows.Next() {
		var m Memory
		if err := rows.Scan(&m.ID, &m.Type, &m.Content, &m.Tags, &m.Source, &m.CreatedAt, &m.Hash); err != nil {
			return d, err
		}
		m.Namespace = namespace
		d.NewMemories = append(d.NewMemories, m)
		d.ByType[m.Type]++
		d.Added++
	}
	return d, rows.Err()
}

// EmbeddingStatus mirrors what `embeddings status` returns per namespace.
type EmbeddingStatus struct {
	Namespace        string  `json:"namespace"`
	Total            int     `json:"total"`
	Embedded         int     `json:"embedded"`
	Unembedded       int     `json:"unembedded"`
	CoveragePercent  float64 `json:"coverage_percent"`
	OldestUnembedded string  `json:"oldest_unembedded,omitempty"`
}

// EmbedStatus reports embedding coverage. If the vec table is missing for a
// namespace, that namespace's coverage is 0% (every row counts as unembedded).
func EmbedStatus(ctx context.Context, selector string) ([]EmbeddingStatus, error) {
	namespaces, err := resolveNamespaces(selector)
	if err != nil {
		return nil, err
	}
	var out []EmbeddingStatus
	for _, ns := range namespaces {
		db, err := OpenReadOnly(ctx, ns)
		if err != nil {
			continue
		}
		s := EmbeddingStatus{Namespace: ns}
		_ = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM memories`).Scan(&s.Total)

		var hasVec int
		_ = db.QueryRowContext(ctx,
			`SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories_vec' LIMIT 1`).
			Scan(&hasVec)
		if hasVec == 1 {
			_ = db.QueryRowContext(ctx,
				`SELECT COUNT(*) FROM memories_vec`).Scan(&s.Embedded)
			s.Unembedded = s.Total - s.Embedded
			if s.Total > 0 {
				s.CoveragePercent = (float64(s.Embedded) / float64(s.Total)) * 100
			}
			_ = db.QueryRowContext(ctx,
				`SELECT MIN(m.created_at) FROM memories m WHERE m.id NOT IN (SELECT id FROM memories_vec)`).
				Scan(nullableScan{&s.OldestUnembedded})
		} else {
			s.Embedded = 0
			s.Unembedded = s.Total
		}
		_ = db.Close()
		out = append(out, s)
	}
	return out, nil
}
