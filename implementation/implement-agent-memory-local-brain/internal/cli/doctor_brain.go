// Brain-specific doctor probe — hand-authored Phase 3 helper, lifted out of
// internal/brain to avoid the import cycle (automation imports brain; brain/doctor
// would have to import automation).
package cli

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"runtime"
	"time"

	"local-brain-pp-cli/internal/brain"
	"local-brain-pp-cli/internal/brain/automation"
	"local-brain-pp-cli/internal/brain/sched"
)

type brainDoctorReport struct {
	OK                 bool              `json:"ok"`
	BrainDirExists     bool              `json:"brain_dir_exists"`
	BrainDir           string            `json:"brain_dir"`
	TotalMemories      int               `json:"total_memories"`
	TotalNamespaces    int               `json:"total_namespaces"`
	SqliteVecAvailable bool              `json:"sqlite_vec_available"`
	ModelCached        bool              `json:"model_cached"`
	PythonBin          string            `json:"python_bin"`
	KiroCLIPath        string            `json:"kiro_cli_path"`
	Schedule           map[string]int    `json:"schedule"`
	Automations        map[string]string `json:"automations"`
	Namespaces         []brain.NamespaceCount `json:"namespaces,omitempty"`
	BinDirReady        bool              `json:"bin_dir_ready"`
	Warnings           []string          `json:"warnings"`
	Platform           string            `json:"platform"`
}

func brainDoctor(ctx context.Context, full bool) brainDoctorReport {
	r := brainDoctorReport{
		BrainDir:    brain.BrainDir(),
		Platform:    runtime.GOOS,
		Schedule:    map[string]int{},
		Automations: map[string]string{},
	}
	r.OK = true

	if _, err := os.Stat(r.BrainDir); err == nil {
		r.BrainDirExists = true
	} else {
		r.Warnings = append(r.Warnings, "brain dir missing — run `local-brain-pp-cli init`")
		r.OK = false
	}

	namespaces, _ := brain.ListNamespaces()
	r.TotalNamespaces = len(namespaces)

	if full {
		nsCounts, _ := brain.NamespaceList(ctx, "")
		r.Namespaces = nsCounts
		for _, n := range nsCounts {
			r.TotalMemories += n.Count
		}
	} else {
		for _, ns := range namespaces {
			db, err := brain.OpenReadOnly(ctx, ns)
			if err != nil {
				continue
			}
			var n int
			_ = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM memories`).Scan(&n)
			_ = db.Close()
			r.TotalMemories += n
		}
	}

	// Python + sqlite-vec
	bin, _ := brain.ProbePythons()
	r.PythonBin = bin
	r.SqliteVecAvailable = bin != ""
	if !r.SqliteVecAvailable {
		r.Warnings = append(r.Warnings, "no Python with sqlite-vec + sentence-transformers — run `embeddings check-deps`, or pip install sqlite-vec sentence-transformers")
	}

	// Embedding model cache
	r.ModelCached = sentenceTransformerCacheExists()

	// agent CLI on PATH (configured via LB_AGENT_CLI env var)
	if path, err := exec.LookPath(os.Getenv("LB_AGENT_CLI")); err == nil {
		r.KiroCLIPath = path
	}


	// Schedule entries
	entries, _ := sched.List(ctx, "", false)
	for _, e := range entries {
		r.Schedule[e.Type]++
	}

	// Automation log freshness
	for _, name := range automation.MemoryAutomations {
		path := automation.MemoryLogPath(name)
		if info, err := os.Stat(path); err == nil {
			r.Automations[name] = info.ModTime().UTC().Format(time.RFC3339)
		} else if !errors.Is(err, os.ErrNotExist) {
			r.Automations[name] = "error: " + err.Error()
		}
	}

	if _, err := os.Stat(r.BrainDir + "/bin"); err == nil {
		r.BinDirReady = true
	} else {
		r.Warnings = append(r.Warnings, "~/.local-brain/bin/ missing — run `local-brain-pp-cli init` to vendor automation scripts")
	}

	if len(r.Warnings) > 0 {
		r.OK = false
	}
	return r
}

func sentenceTransformerCacheExists() bool {
	home, err := os.UserHomeDir()
	if err != nil {
		return false
	}
	candidates := []string{
		home + "/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2",
		home + "/.cache/torch/sentence_transformers/sentence-transformers_all-MiniLM-L6-v2",
	}
	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return true
		}
	}
	return false
}

