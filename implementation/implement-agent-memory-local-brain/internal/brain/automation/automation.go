// Package automation implements the surface that wraps the 9 vendored
// lb-memory-* shell scripts plus generic user-defined custom automations.
//
// The 9 memory automations are well-known names with fixed schedules; we
// don't accept arbitrary names there. The custom automation surface is the
// Custom user-defined memory automations: each task gets a directory under
// ~/.local-brain/automations/<id>/
// containing task.json, run.sh, last-run.log, .lock, state.json.
package automation

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"local-brain-pp-cli/internal/brain"
)

// MemoryAutomations lists the 9 well-known automation names. Order matters
// for `automation memory list` output.
var MemoryAutomations = []string{
	"embedder",
	"indexer",
	"compiler",
	"linter",
	"enricher",
	"pruner",
	"rollup",
	"exporter",
	"migrate-namespaces",
}

// MemoryAutomation describes one well-known memory automation's status.
type MemoryAutomation struct {
	Name     string `json:"name"`
	Schedule string `json:"schedule"`
	Enabled  bool   `json:"enabled"`
	Locked   bool   `json:"locked"`
	LastRun  string `json:"last_run"`
	NextRun  string `json:"next_run"`
	LogPath  string `json:"log_path"`
}

// MemoryAutomationStatus is the per-name status returned by `status <name>`.
type MemoryAutomationStatus struct {
	Name    string `json:"name"`
	Enabled bool   `json:"enabled"`
	Locked  bool   `json:"locked"`
	LastRun string `json:"last_run"`
	NextRun string `json:"next_run"`
	LogTail string `json:"log_tail"`
}

// AutomationRunResult mirrors the spec.
type AutomationRunResult struct {
	Name    string `json:"name"`
	ID      string `json:"id,omitempty"`
	Started bool   `json:"started"`
	PID     int    `json:"pid,omitempty"`
	LogPath string `json:"log_path,omitempty"`
}

// LogResult is the shared shape for memory + custom logs subcommands.
type LogResult struct {
	Path  string   `json:"path"`
	Lines []string `json:"lines"`
	Bytes int      `json:"bytes"`
}

// LogDir is the directory where lb-memory-*.sh writes their logs. Mirrors
// the path baked into every script: $HOME/.local-brain/logs.
func LogDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".local-brain", "logs")
}

// MemoryLogPath is the canonical log file for a given memory automation.
func MemoryLogPath(name string) string {
	return filepath.Join(LogDir(), "memory-"+name+".log")
}

// VendoredScript returns the absolute path to the vendored shell script for a
// memory automation. After `local-brain init`, every script lives at
// ~/.local-brain/bin/lb-memory-<name>.sh.
func VendoredScript(name string) string {
	return filepath.Join(brain.BrainDir(), "bin", "lb-memory-"+name+".sh")
}

// ScheduleLabel is the launchd Label / cron marker used by the schedule
// manager. Memory automations get a stable label per name so installs are
// idempotent. Uses a `com.localbrain.memory-<name>` launchd label.
// `enable` produces an idempotent entry.
func ScheduleLabel(name string) string {
	return "com.localbrain.memory-" + name
}

// IsValidMemoryName reports whether `name` is one of the 9 well-known automations.
func IsValidMemoryName(name string) bool {
	for _, n := range MemoryAutomations {
		if n == name {
			return true
		}
	}
	return false
}

// ListMemoryAutomations returns status for every well-known memory automation,
// reading lock files / log timestamps directly. Schedule fields come from
// schedule.Manager (the caller usually merges those in; here we leave them blank).
func ListMemoryAutomations() ([]MemoryAutomation, error) {
	out := make([]MemoryAutomation, 0, len(MemoryAutomations))
	for _, name := range MemoryAutomations {
		ma := MemoryAutomation{
			Name:    name,
			LogPath: MemoryLogPath(name),
		}
		// Lock files use $LOG_DIR/memory-<name>-YYYYMMDD.lock for daily; weekly
		// uses YYYY-WNN. We just check whether *any* lock file exists today.
		ma.Locked = anyLockToday(name)
		// Last run: log file mtime is a fine proxy.
		if info, err := os.Stat(ma.LogPath); err == nil {
			ma.LastRun = info.ModTime().UTC().Format(time.RFC3339)
		}
		out = append(out, ma)
	}
	return out, nil
}

func anyLockToday(name string) bool {
	dir := LogDir()
	pattern := "memory-" + name + "-*.lock"
	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil || len(matches) == 0 {
		return false
	}
	today := time.Now().UTC().Format("20060102")
	week := time.Now().UTC().Format("2006-W") // launchd locks may use Y-WNN
	_ = week
	for _, m := range matches {
		if strings.Contains(m, today) {
			return true
		}
	}
	return false
}

// MemoryStatus returns the rich status for one well-known automation,
// including the last 30 lines of its log.
func MemoryStatus(name string) (MemoryAutomationStatus, error) {
	if !IsValidMemoryName(name) {
		return MemoryAutomationStatus{}, fmt.Errorf("unknown memory automation %q (valid: %s)", name, strings.Join(MemoryAutomations, ", "))
	}
	logPath := MemoryLogPath(name)
	st := MemoryAutomationStatus{Name: name, Locked: anyLockToday(name)}
	if info, err := os.Stat(logPath); err == nil {
		st.LastRun = info.ModTime().UTC().Format(time.RFC3339)
	}
	if data, err := tailFile(logPath, 30); err == nil {
		st.LogTail = data
	}
	return st, nil
}

// MemoryLogs reads a tail of the named automation's log file. Pass tail==0
// for a default of 200 lines.
func MemoryLogs(name string, tail int, since string) (LogResult, error) {
	if !IsValidMemoryName(name) {
		return LogResult{}, fmt.Errorf("unknown memory automation %q", name)
	}
	if tail <= 0 {
		tail = 200
	}
	path := MemoryLogPath(name)
	body, err := tailFile(path, tail)
	if err != nil {
		return LogResult{Path: path}, err
	}
	lines := strings.Split(strings.TrimRight(body, "\n"), "\n")
	return LogResult{Path: path, Lines: lines, Bytes: len(body)}, nil
}

// RunMemoryNow shells out to ~/.local-brain/bin/lb-memory-<name>.sh.
// When force=true, sets FORCE_RUN=true (the shared shell pattern). When
// wait=false, the process is detached and we return immediately.
func RunMemoryNow(ctx context.Context, name, namespace string, force, wait bool) (AutomationRunResult, error) {
	if !IsValidMemoryName(name) {
		return AutomationRunResult{}, fmt.Errorf("unknown memory automation %q", name)
	}
	script := VendoredScript(name)
	if _, err := os.Stat(script); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return AutomationRunResult{}, fmt.Errorf("script not installed (run `local-brain-pp-cli init`); expected at %s", script)
		}
		return AutomationRunResult{}, err
	}
	cmd := exec.CommandContext(ctx, "bash", script)
	cmd.Env = os.Environ()
	if force {
		cmd.Env = append(cmd.Env, "FORCE_RUN=true")
	}
	if namespace != "" {
		cmd.Env = append(cmd.Env, "NEO_AUTOMATION_NAMESPACE="+namespace)
	}
	if wait {
		out, err := cmd.CombinedOutput()
		if err != nil {
			return AutomationRunResult{Name: name, Started: false, LogPath: MemoryLogPath(name)}, fmt.Errorf("run failed: %w\n%s", err, string(out))
		}
		return AutomationRunResult{Name: name, Started: true, LogPath: MemoryLogPath(name)}, nil
	}
	cmd.Stdout = nil
	cmd.Stderr = nil
	if err := cmd.Start(); err != nil {
		return AutomationRunResult{Name: name, Started: false}, err
	}
	return AutomationRunResult{Name: name, Started: true, PID: cmd.Process.Pid, LogPath: MemoryLogPath(name)}, nil
}

// tailFile returns the last `n` lines of a file. Cheap-and-cheerful: read all
// then split. Adequate for our log sizes (capped at ~10MB by the rotating
// `find -mtime +30 -delete` cleanup the scripts run).
func tailFile(path string, n int) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	body, err := io.ReadAll(f)
	if err != nil {
		return "", err
	}
	lines := strings.Split(strings.TrimRight(string(body), "\n"), "\n")
	if len(lines) > n {
		lines = lines[len(lines)-n:]
	}
	return strings.Join(lines, "\n") + "\n", nil
}

// ----- Custom user-defined automations -----

// CustomAutomation mirrors automations.py's task.json + runtime fields.
type CustomAutomation struct {
	ID        string         `json:"id"`
	Name      string         `json:"name"`
	Prompt    string         `json:"prompt"`
	Schedule  map[string]any `json:"schedule"`
	Agent     string         `json:"agent"`
	Enabled   bool           `json:"enabled"`
	CreatedAt string         `json:"created_at"`
	LastRun   string         `json:"last_run,omitempty"`
	NextRun   string         `json:"next_run,omitempty"`
	Locked    bool           `json:"locked,omitempty"`
}

// AutomationsDir is where custom-task subdirectories live, mirroring
// automations live under: ~/.local-brain/automations/.
func AutomationsDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".local-brain", "automations")
}

// TaskDir returns the subdirectory for one custom automation.
func TaskDir(id string) string {
	return filepath.Join(AutomationsDir(), id)
}

// SanitizeID converts a name to a safe directory ID (lowercase, kebab).
func SanitizeID(name string) string {
	out := strings.ToLower(strings.TrimSpace(name))
	var b strings.Builder
	for _, r := range out {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
			b.WriteRune(r)
		} else {
			b.WriteRune('-')
		}
	}
	id := b.String()
	id = strings.Trim(id, "-")
	if len(id) > 50 {
		id = id[:50]
	}
	return id
}

// ListCustom returns every custom automation, sorted by id.
func ListCustom(enabledOnly bool, filter string) ([]CustomAutomation, error) {
	dir := AutomationsDir()
	entries, err := os.ReadDir(dir)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	var out []CustomAutomation
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		c, err := loadCustom(e.Name())
		if err != nil {
			continue
		}
		if enabledOnly && !c.Enabled {
			continue
		}
		if filter != "" && !strings.Contains(c.Name, filter) && !strings.Contains(c.ID, filter) {
			continue
		}
		out = append(out, c)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func loadCustom(id string) (CustomAutomation, error) {
	taskFile := filepath.Join(TaskDir(id), "task.json")
	body, err := os.ReadFile(taskFile)
	if err != nil {
		return CustomAutomation{}, err
	}
	var c CustomAutomation
	if err := json.Unmarshal(body, &c); err != nil {
		return c, err
	}
	if c.ID == "" {
		c.ID = id
	}
	c.Locked = fileExists(filepath.Join(TaskDir(id), ".lock"))
	if info, err := os.Stat(filepath.Join(TaskDir(id), "last-run.log")); err == nil {
		c.LastRun = info.ModTime().UTC().Format(time.RFC3339)
	}
	return c, nil
}

func fileExists(p string) bool {
	_, err := os.Stat(p)
	return err == nil
}

// CreateCustomOpts is the input shape for CreateCustom.
type CreateCustomOpts struct {
	Name              string
	Prompt            string
	Schedule          string // human spec like "daily@08:00" or "weekly@monday-09:00"
	Agent             string
	DeliveryEmail     bool
	DeliverySlack     bool
	DeliveryWorkspace bool
}

// CreateCustom writes the task directory and run.sh. Schedule installation is
// handled separately by the schedule package; CreateCustom marks Enabled=true
// and the caller is expected to call schedule.Install afterwards.
func CreateCustom(opts CreateCustomOpts) (CustomAutomation, error) {
	if opts.Name == "" {
		return CustomAutomation{}, errors.New("name is required")
	}
	if opts.Prompt == "" {
		return CustomAutomation{}, errors.New("prompt is required")
	}
	id := SanitizeID(opts.Name)
	if id == "" {
		return CustomAutomation{}, errors.New("name produced empty id")
	}
	dir := TaskDir(id)
	if _, err := os.Stat(dir); err == nil {
		return CustomAutomation{}, fmt.Errorf("automation %q already exists", id)
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return CustomAutomation{}, err
	}
	c := CustomAutomation{
		ID:        id,
		Name:      opts.Name,
		Prompt:    opts.Prompt,
		Agent:     opts.Agent,
		Enabled:   true,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
	}
	if c.Agent == "" {
		c.Agent = os.Getenv("LB_AGENT_NAME")
	}
	if opts.Schedule == "" {
		opts.Schedule = "daily@08:00"
	}
	c.Schedule = parseScheduleSpec(opts.Schedule)
	if c.Schedule == nil {
		return CustomAutomation{}, fmt.Errorf("could not parse schedule spec %q", opts.Schedule)
	}
	taskJSON, _ := json.MarshalIndent(c, "", "  ")
	if err := os.WriteFile(filepath.Join(dir, "task.json"), taskJSON, 0o644); err != nil {
		return c, err
	}
	if err := writeRunScript(c, opts); err != nil {
		return c, err
	}
	return c, nil
}

func writeRunScript(c CustomAutomation, opts CreateCustomOpts) error {
	dir := TaskDir(c.ID)
	homeDocs := os.ExpandEnv("$HOME/Documents/neo-workspace")
	var b strings.Builder
	b.WriteString("#!/bin/bash -l\n")
	fmt.Fprintf(&b, "# Auto-generated by local-brain-pp-cli for: %s\n", c.Name)
	b.WriteString("export PATH=\"$HOME/.local/bin:$HOME/.toolbox/bin:/usr/local/bin:$PATH\"\n")
	fmt.Fprintf(&b, "TASK_DIR=\"%s\"\n", dir)
	b.WriteString("LOG=\"$TASK_DIR/last-run.log\"\n")
	b.WriteString("STATE=\"$TASK_DIR/state.json\"\n")
	b.WriteString("LOCK=\"$TASK_DIR/.lock\"\n\n")
	b.WriteString("[ -f \"$LOCK\" ] && exit 0\n")
	b.WriteString("touch \"$LOCK\"\n")
	b.WriteString("trap \"rm -f $LOCK\" EXIT\n\n")
	b.WriteString("PROMPT=\"Today is $(date '+%A, %B %d, %Y at %I:%M %p').\"\n")
	b.WriteString("if [ -f \"$STATE\" ] && [ -s \"$STATE\" ]; then\n")
	b.WriteString("    STATE_CONTENT=$(cat \"$STATE\")\n")
	b.WriteString("    PROMPT=\"$PROMPT Previous run summary: $STATE_CONTENT\"\n")
	b.WriteString("fi\n")
	escapedPrompt := strings.ReplaceAll(c.Prompt, `"`, `\"`)
	escapedPrompt = strings.ReplaceAll(escapedPrompt, "$", `\$`)
	fmt.Fprintf(&b, "PROMPT=\"$PROMPT %s\"\n", escapedPrompt)
	if opts.DeliveryWorkspace {
		fmt.Fprintf(&b, "PROMPT=\"$PROMPT Save any output files to %s/\"\n", homeDocs)
	}
	if opts.DeliveryEmail {
		b.WriteString("PROMPT=\"$PROMPT Email the results to me.\"\n")
	}
	if opts.DeliverySlack {
		b.WriteString("PROMPT=\"$PROMPT Send results via Slack DM.\"\n")
	}
	b.WriteString("PROMPT=\"$PROMPT After completing, write a brief JSON summary of key findings to $STATE for continuity in the next run.\"\n")
	b.WriteString("PROMPT=\"$PROMPT [Do NOT spawn subagents — handle directly with your MCP tools.]\"\n\n")
	agentCLI := os.Getenv("LB_AGENT_CLI")
	if agentCLI == "" {
		agentCLI = "agent-cli"
	}
	agentArgs := os.Getenv("LB_AGENT_ARGS")
	if agentArgs == "" {
		agentArgs = "--no-interactive"
	}
	if c.Agent != "" {
		fmt.Fprintf(&b, "%s --agent %s %s \"$PROMPT\" > \"$LOG\" 2>&1\n", agentCLI, c.Agent, agentArgs)
	} else {
		fmt.Fprintf(&b, "%s %s \"$PROMPT\" > \"$LOG\" 2>&1\n", agentCLI, agentArgs)
	}

	runPath := filepath.Join(dir, "run.sh")
	if err := os.WriteFile(runPath, []byte(b.String()), 0o755); err != nil {
		return err
	}
	return nil
}

// UpdateCustom partially modifies a custom automation. Empty-string and false
// fields in opts are ignored.
type UpdateCustomOpts struct {
	Prompt   string
	Schedule string
	Enabled  *bool
	Agent    string
}

func UpdateCustom(id string, opts UpdateCustomOpts) (CustomAutomation, error) {
	c, err := loadCustom(id)
	if err != nil {
		return c, err
	}
	if opts.Prompt != "" {
		c.Prompt = opts.Prompt
	}
	if opts.Schedule != "" {
		c.Schedule = parseScheduleSpec(opts.Schedule)
	}
	if opts.Enabled != nil {
		c.Enabled = *opts.Enabled
	}
	if opts.Agent != "" {
		c.Agent = opts.Agent
	}
	taskJSON, _ := json.MarshalIndent(c, "", "  ")
	if err := os.WriteFile(filepath.Join(TaskDir(id), "task.json"), taskJSON, 0o644); err != nil {
		return c, err
	}
	// Regenerate run.sh — preserve delivery flags conservatively (we don't
	// store them on disk per-se; the run script is rewritten with whatever
	// was last specified, defaulting to workspace=true).
	if err := writeRunScript(c, CreateCustomOpts{
		Name: c.Name, Prompt: c.Prompt, Schedule: opts.Schedule, Agent: c.Agent,
		DeliveryWorkspace: true,
	}); err != nil {
		return c, err
	}
	return c, nil
}

// DeleteCustom removes the task directory. The schedule entry must be
// uninstalled separately by the caller (or scheduler manager).
func DeleteCustom(id string, keepLogs bool) error {
	dir := TaskDir(id)
	if _, err := os.Stat(dir); err != nil {
		return fmt.Errorf("automation %q not found", id)
	}
	if !keepLogs {
		return os.RemoveAll(dir)
	}
	// Selective removal: keep last-run.log and state.json
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	for _, e := range entries {
		switch e.Name() {
		case "last-run.log", "state.json", "launchd-stdout.log", "launchd-stderr.log":
			continue
		default:
			_ = os.RemoveAll(filepath.Join(dir, e.Name()))
		}
	}
	return nil
}

// RunCustomNow executes run.sh in the background (or synchronously when wait=true).
func RunCustomNow(ctx context.Context, id string, wait bool) (AutomationRunResult, error) {
	runPath := filepath.Join(TaskDir(id), "run.sh")
	if _, err := os.Stat(runPath); err != nil {
		return AutomationRunResult{}, fmt.Errorf("run.sh not found for %q", id)
	}
	cmd := exec.CommandContext(ctx, "bash", runPath)
	if wait {
		out, err := cmd.CombinedOutput()
		if err != nil {
			return AutomationRunResult{ID: id, Started: false}, fmt.Errorf("run failed: %w\n%s", err, string(out))
		}
		return AutomationRunResult{ID: id, Started: true, LogPath: filepath.Join(TaskDir(id), "last-run.log")}, nil
	}
	cmd.Stdout = nil
	cmd.Stderr = nil
	if err := cmd.Start(); err != nil {
		return AutomationRunResult{ID: id, Started: false}, err
	}
	return AutomationRunResult{ID: id, Started: true, PID: cmd.Process.Pid, LogPath: filepath.Join(TaskDir(id), "last-run.log")}, nil
}

// CustomLogs reads last-run.log for a custom automation.
func CustomLogs(id string, tail int) (LogResult, error) {
	if tail <= 0 {
		tail = 200
	}
	path := filepath.Join(TaskDir(id), "last-run.log")
	body, err := tailFile(path, tail)
	if err != nil {
		return LogResult{Path: path}, err
	}
	lines := strings.Split(strings.TrimRight(body, "\n"), "\n")
	return LogResult{Path: path, Lines: lines, Bytes: len(body)}, nil
}

// CustomState returns the parsed JSON state file for a custom automation.
func CustomState(id string) (map[string]any, error) {
	path := filepath.Join(TaskDir(id), "state.json")
	body, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return map[string]any{}, nil
		}
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(body, &out); err != nil {
		// Fall back to raw payload so the caller still sees something.
		return map[string]any{"raw": string(body)}, nil
	}
	return out, nil
}

// parseScheduleSpec converts a human spec ("daily@08:00", "weekly@monday-09:00",
// "hourly@:30", "every-15m") into a structured schedule map. Returns nil for
// unrecognized specs.
func parseScheduleSpec(spec string) map[string]any {
	spec = strings.TrimSpace(spec)
	if spec == "" {
		return nil
	}
	// daily@HH:MM
	if strings.HasPrefix(spec, "daily@") {
		t := strings.TrimPrefix(spec, "daily@")
		return map[string]any{"type": "daily", "time": t}
	}
	// weekly@day-HH:MM
	if strings.HasPrefix(spec, "weekly@") {
		body := strings.TrimPrefix(spec, "weekly@")
		parts := strings.SplitN(body, "-", 2)
		if len(parts) == 2 {
			return map[string]any{"type": "weekly", "day": parts[0], "time": parts[1]}
		}
	}
	// hourly@:MM
	if strings.HasPrefix(spec, "hourly@") {
		t := strings.TrimPrefix(spec, "hourly@:")
		return map[string]any{"type": "hourly", "minute": t}
	}
	// every-NNm  -> every N minutes
	if strings.HasPrefix(spec, "every-") {
		v := strings.TrimPrefix(spec, "every-")
		return map[string]any{"type": "every", "value": v}
	}
	// Assume raw cron expression as fallback.
	return map[string]any{"type": "cron", "expr": spec}
}

// EnsureBin makes sure the brain bin directory exists. Used by `init`.
func EnsureBin() error {
	return os.MkdirAll(filepath.Join(brain.BrainDir(), "bin"), 0o755)
}

// WalkBinScripts walks an embed.FS rooted at "scripts/" and copies every file
// to ~/.local-brain/bin/. The init command bundles the 11 lb-memory-*.sh
// scripts via go:embed; this helper is the writer.
func WalkBinScripts(efs fs.FS, force bool) ([]string, error) {
	if err := EnsureBin(); err != nil {
		return nil, err
	}
	dst := filepath.Join(brain.BrainDir(), "bin")
	var written []string
	err := fs.WalkDir(efs, "scripts", func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}
		base := filepath.Base(path)
		out := filepath.Join(dst, base)
		if !force {
			if _, err := os.Stat(out); err == nil {
				return nil
			}
		}
		body, err := fs.ReadFile(efs, path)
		if err != nil {
			return err
		}
		if err := os.WriteFile(out, body, 0o755); err != nil {
			return err
		}
		written = append(written, out)
		return nil
	})
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return written, err
	}
	return written, nil
}

// PlatformID returns "macos" or "linux" — used by the schedule manager to
// decide between launchd and crontab.
func PlatformID() string {
	if runtime.GOOS == "darwin" {
		return "macos"
	}
	return "linux"
}
