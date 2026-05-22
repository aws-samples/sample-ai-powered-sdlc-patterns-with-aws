// Package sched manages cross-platform schedule entries for local-brain
// memory + custom automations. macOS uses launchd plists at
// ~/Library/LaunchAgents; Linux/WSL uses crontab markers (`# local-brain-<type>-<name>`).
package sched

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"local-brain-pp-cli/internal/brain"
)

// Entry describes one schedule registration.
type Entry struct {
	Type          string `json:"type"`           // "memory" or "custom"
	Name          string `json:"name"`           // memory: well-known name; custom: id
	Platform      string `json:"platform"`       // "launchd" or "cron"
	ScheduleLabel string `json:"schedule_label"` // launchd Label or cron marker
	CronExpr      string `json:"cron_expr"`
	Enabled       bool   `json:"enabled"`
	NextRun       string `json:"next_run,omitempty"`
}

// PlistDir is where launchd plists live on macOS.
func PlistDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, "Library", "LaunchAgents")
}

// IsMacOS reports whether we're running on macOS (launchd path).
func IsMacOS() bool { return runtime.GOOS == "darwin" }

// LabelMemory returns the canonical launchd Label / cron marker for a memory automation.
func LabelMemory(name string) string {
	return "com.localbrain.memory-" + name
}

// LabelCustom returns the canonical launchd Label / cron marker for a custom automation.
func LabelCustom(id string) string {
	return "com.localbrain.custom." + id
}

// List returns every schedule entry the local-brain CLI knows about, scanning
// both launchd plists (macOS) and crontab markers (Linux/WSL). Memory and
// custom automations are merged into one chronological view.
func List(ctx context.Context, typeFilter string, enabledOnly bool) ([]Entry, error) {
	var entries []Entry
	if IsMacOS() {
		me, err := scanLaunchd()
		if err != nil {
			return nil, err
		}
		entries = me
	} else {
		ce, err := scanCron(ctx)
		if err != nil {
			return nil, err
		}
		entries = ce
	}
	if typeFilter != "" {
		filtered := make([]Entry, 0, len(entries))
		for _, e := range entries {
			if e.Type == typeFilter {
				filtered = append(filtered, e)
			}
		}
		entries = filtered
	}
	if enabledOnly {
		filtered := make([]Entry, 0, len(entries))
		for _, e := range entries {
			if e.Enabled {
				filtered = append(filtered, e)
			}
		}
		entries = filtered
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Type != entries[j].Type {
			return entries[i].Type < entries[j].Type
		}
		return entries[i].Name < entries[j].Name
	})
	return entries, nil
}

// scanLaunchd looks for plists named com.localbrain.memory-* and com.localbrain.custom.*.
func scanLaunchd() ([]Entry, error) {
	dir := PlistDir()
	entries, err := os.ReadDir(dir)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	var out []Entry
	for _, e := range entries {
		name := e.Name()
		if !strings.HasSuffix(name, ".plist") {
			continue
		}
		label := strings.TrimSuffix(name, ".plist")
		var entry Entry
		switch {
		case strings.HasPrefix(label, "com.localbrain.memory-"):
			entry = Entry{
				Type:          "memory",
				Name:          strings.TrimPrefix(label, "com.localbrain.memory-"),
				Platform:      "launchd",
				ScheduleLabel: label,
				Enabled:       true, // existence implies installed; we don't probe `launchctl list` here
			}
		case strings.HasPrefix(label, "com.localbrain.custom."):
			entry = Entry{
				Type:          "custom",
				Name:          strings.TrimPrefix(label, "com.localbrain.custom."),
				Platform:      "launchd",
				ScheduleLabel: label,
				Enabled:       true,
			}
		default:
			continue
		}
		out = append(out, entry)
	}
	return out, nil
}

// scanCron parses crontab -l for our markers. Marker patterns:
//   memory: `# local-brain-memory-<name>`
//   custom: `# neo-custom-<id>` (legacy compatibility marker)
func scanCron(ctx context.Context) ([]Entry, error) {
	out, err := exec.CommandContext(ctx, "crontab", "-l").Output()
	if err != nil {
		// Empty crontab returns non-zero on some systems; treat as no entries.
		return nil, nil
	}
	var entries []Entry
	for _, line := range strings.Split(string(out), "\n") {
		l := strings.TrimSpace(line)
		if l == "" || strings.HasPrefix(l, "#") {
			continue
		}
		// Format: "<cron expr> <command> # <marker>"
		hash := strings.Index(l, "#")
		if hash < 0 {
			continue
		}
		marker := strings.TrimSpace(l[hash+1:])
		body := strings.TrimSpace(l[:hash])
		fields := strings.Fields(body)
		if len(fields) < 6 {
			continue
		}
		cronExpr := strings.Join(fields[:5], " ")

		var e Entry
		switch {
		case strings.HasPrefix(marker, "local-brain-memory-"):
			e = Entry{
				Type:          "memory",
				Name:          strings.TrimPrefix(marker, "local-brain-memory-"),
				Platform:      "cron",
				ScheduleLabel: marker,
				CronExpr:      cronExpr,
				Enabled:       true,
			}
		case strings.HasPrefix(marker, "neo-custom-"):
			e = Entry{
				Type:          "custom",
				Name:          strings.TrimPrefix(marker, "neo-custom-"),
				Platform:      "cron",
				ScheduleLabel: marker,
				CronExpr:      cronExpr,
				Enabled:       true,
			}
		default:
			continue
		}
		entries = append(entries, e)
	}
	return entries, nil
}

// InstallMemory writes a launchd plist (or appends a crontab line) for a
// well-known memory automation. Idempotent: replaces an existing entry.
func InstallMemory(ctx context.Context, name string, scheduleSpec string) error {
	script := filepath.Join(brain.BrainDir(), "bin", "lb-memory-"+name+".sh")
	if _, err := os.Stat(script); err != nil {
		return fmt.Errorf("script not installed (run init): %s", script)
	}
	if IsMacOS() {
		return installLaunchd(ctx, LabelMemory(name), script, scheduleSpec)
	}
	return installCron(ctx, "local-brain-memory-"+name, script, scheduleSpec)
}

// UninstallMemory removes the launchd plist or crontab line for a memory automation.
func UninstallMemory(ctx context.Context, name string) error {
	if IsMacOS() {
		return uninstallLaunchd(ctx, LabelMemory(name))
	}
	return uninstallCron(ctx, "local-brain-memory-"+name)
}

// InstallCustom installs the schedule for a custom automation given its
// run.sh path and schedule spec.
func InstallCustom(ctx context.Context, id, runScript, scheduleSpec string) error {
	if IsMacOS() {
		return installLaunchd(ctx, LabelCustom(id), runScript, scheduleSpec)
	}
	return installCron(ctx, "neo-custom-"+id, runScript, scheduleSpec)
}

// UninstallCustom removes the schedule entry for a custom automation.
func UninstallCustom(ctx context.Context, id string) error {
	if IsMacOS() {
		return uninstallLaunchd(ctx, LabelCustom(id))
	}
	return uninstallCron(ctx, "neo-custom-"+id)
}

func installLaunchd(ctx context.Context, label, script, scheduleSpec string) error {
	dir := PlistDir()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	plistPath := filepath.Join(dir, label+".plist")
	plistBody := buildPlist(label, script, scheduleSpec)
	// Unload any existing entry first; failures are acceptable when not loaded.
	_ = exec.CommandContext(ctx, "launchctl", "unload", plistPath).Run()
	if err := os.WriteFile(plistPath, []byte(plistBody), 0o644); err != nil {
		return err
	}
	return exec.CommandContext(ctx, "launchctl", "load", plistPath).Run()
}

func uninstallLaunchd(ctx context.Context, label string) error {
	plistPath := filepath.Join(PlistDir(), label+".plist")
	if _, err := os.Stat(plistPath); err != nil {
		return nil // already gone
	}
	_ = exec.CommandContext(ctx, "launchctl", "unload", plistPath).Run()
	return os.Remove(plistPath)
}

func installCron(ctx context.Context, marker, script, scheduleSpec string) error {
	expr := scheduleSpecToCron(scheduleSpec)
	if expr == "" {
		return fmt.Errorf("could not derive cron expression from %q", scheduleSpec)
	}
	out, err := exec.CommandContext(ctx, "crontab", "-l").Output()
	existing := ""
	if err == nil {
		existing = string(out)
	}
	var lines []string
	for _, l := range strings.Split(existing, "\n") {
		if !strings.Contains(l, marker) && strings.TrimSpace(l) != "" {
			lines = append(lines, l)
		}
	}
	lines = append(lines, fmt.Sprintf("%s bash %s # %s", expr, script, marker))
	cmd := exec.CommandContext(ctx, "crontab", "-")
	cmd.Stdin = strings.NewReader(strings.Join(lines, "\n") + "\n")
	return cmd.Run()
}

func uninstallCron(ctx context.Context, marker string) error {
	out, err := exec.CommandContext(ctx, "crontab", "-l").Output()
	if err != nil {
		return nil
	}
	var lines []string
	for _, l := range strings.Split(string(out), "\n") {
		if !strings.Contains(l, marker) && strings.TrimSpace(l) != "" {
			lines = append(lines, l)
		}
	}
	cmd := exec.CommandContext(ctx, "crontab", "-")
	cmd.Stdin = strings.NewReader(strings.Join(lines, "\n") + "\n")
	return cmd.Run()
}

// buildPlist returns a launchd plist for one program.
func buildPlist(label, script, scheduleSpec string) string {
	hour, minute, day := parseDailyOrWeekly(scheduleSpec)
	calendar := fmt.Sprintf(`    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>%d</integer>
        <key>Minute</key>
        <integer>%d</integer>`, hour, minute)
	if day >= 0 {
		calendar += fmt.Sprintf(`
        <key>Weekday</key>
        <integer>%d</integer>`, day)
	}
	calendar += "\n    </dict>"
	home, _ := os.UserHomeDir()
	stdoutPath := filepath.Join(home, ".local-brain", "logs", label+"-stdout.log")
	stderrPath := filepath.Join(home, ".local-brain", "logs", label+"-stderr.log")
	return fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>%s</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-l</string>
        <string>%s</string>
    </array>
%s
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>%s</string>
        <key>HOME</key>
        <string>%s</string>
    </dict>
    <key>StandardOutPath</key>
    <string>%s</string>
    <key>StandardErrorPath</key>
    <string>%s</string>
</dict>
</plist>
`, label, script, calendar, os.Getenv("PATH"), home, stdoutPath, stderrPath)
}

// parseDailyOrWeekly extracts hour/minute/weekday from "daily@HH:MM" or
// "weekly@<day>-HH:MM". Day is -1 for daily.
func parseDailyOrWeekly(spec string) (int, int, int) {
	hour, minute, day := 8, 0, -1
	if strings.HasPrefix(spec, "daily@") {
		t := strings.TrimPrefix(spec, "daily@")
		hour, minute = parseHHMM(t)
	} else if strings.HasPrefix(spec, "weekly@") {
		body := strings.TrimPrefix(spec, "weekly@")
		parts := strings.SplitN(body, "-", 2)
		if len(parts) == 2 {
			day = dayMap(parts[0])
			hour, minute = parseHHMM(parts[1])
		}
	} else if strings.HasPrefix(spec, "hourly@") {
		hour = -1 // signal: every hour
		minStr := strings.TrimPrefix(spec, "hourly@:")
		fmt.Sscanf(minStr, "%d", &minute)
	}
	return hour, minute, day
}

// scheduleSpecToCron converts our human spec to a crontab expression.
func scheduleSpecToCron(spec string) string {
	if strings.HasPrefix(spec, "daily@") {
		hh, mm := parseHHMM(strings.TrimPrefix(spec, "daily@"))
		return fmt.Sprintf("%d %d * * *", mm, hh)
	}
	if strings.HasPrefix(spec, "weekly@") {
		body := strings.TrimPrefix(spec, "weekly@")
		parts := strings.SplitN(body, "-", 2)
		if len(parts) == 2 {
			d := dayMap(parts[0])
			hh, mm := parseHHMM(parts[1])
			return fmt.Sprintf("%d %d * * %d", mm, hh, d)
		}
	}
	if strings.HasPrefix(spec, "hourly@:") {
		mm := 0
		fmt.Sscanf(strings.TrimPrefix(spec, "hourly@:"), "%d", &mm)
		return fmt.Sprintf("%d * * * *", mm)
	}
	if strings.HasPrefix(spec, "every-") {
		// every-15m -> */15 * * * *
		v := strings.TrimSuffix(strings.TrimPrefix(spec, "every-"), "m")
		return "*/" + v + " * * * *"
	}
	// Treat anything else as a raw cron expression.
	if len(strings.Fields(spec)) >= 5 {
		return spec
	}
	return ""
}

func parseHHMM(s string) (int, int) {
	parts := strings.SplitN(s, ":", 2)
	hh, mm := 8, 0
	if len(parts) > 0 {
		fmt.Sscanf(parts[0], "%d", &hh)
	}
	if len(parts) > 1 {
		fmt.Sscanf(parts[1], "%d", &mm)
	}
	return hh, mm
}

func dayMap(d string) int {
	switch strings.ToLower(d) {
	case "sunday":
		return 0
	case "monday":
		return 1
	case "tuesday":
		return 2
	case "wednesday":
		return 3
	case "thursday":
		return 4
	case "friday":
		return 5
	case "saturday":
		return 6
	}
	return 1
}

// NextRun is the simulator's row.
type NextRun struct {
	Type     string    `json:"type"`
	Name     string    `json:"name"`
	At       time.Time `json:"at"`
	CronExpr string    `json:"cron_expr,omitempty"`
}

// NextRuns simulates the next `hours` of automation fires across all known
// entries. Uses a simple cron parser supporting `M H D Mo W` with `*`,
// `*/N`, and integer literals — adequate for the limited expressions our
// installer produces. Returns sorted ascending by time.
func NextRuns(ctx context.Context, hours int) ([]NextRun, error) {
	if hours <= 0 {
		hours = 24
	}
	entries, err := List(ctx, "", false)
	if err != nil {
		return nil, err
	}
	now := time.Now()
	end := now.Add(time.Duration(hours) * time.Hour)
	var fires []NextRun
	for _, e := range entries {
		expr := e.CronExpr
		if expr == "" && IsMacOS() {
			// Read the plist back to derive a cron expression.
			expr = derivePlistCron(e.ScheduleLabel)
			e.CronExpr = expr
		}
		if expr == "" {
			continue
		}
		fs, err := simulateCron(expr, now, end)
		if err != nil {
			continue
		}
		for _, t := range fs {
			fires = append(fires, NextRun{Type: e.Type, Name: e.Name, At: t, CronExpr: expr})
		}
	}
	sort.Slice(fires, func(i, j int) bool { return fires[i].At.Before(fires[j].At) })
	return fires, nil
}

// derivePlistCron reads the plist file and infers a cron expression from
// StartCalendarInterval. Best-effort; returns "" if unreadable.
func derivePlistCron(label string) string {
	body, err := os.ReadFile(filepath.Join(PlistDir(), label+".plist"))
	if err != nil {
		return ""
	}
	hour, minute, weekday := -1, -1, -1
	chunk := string(body)
	hour = readPlistInteger(chunk, "Hour")
	minute = readPlistInteger(chunk, "Minute")
	weekday = readPlistInteger(chunk, "Weekday")
	if minute < 0 {
		minute = 0
	}
	if weekday >= 0 && hour >= 0 {
		return fmt.Sprintf("%d %d * * %d", minute, hour, weekday)
	}
	if hour >= 0 {
		return fmt.Sprintf("%d %d * * *", minute, hour)
	}
	if minute >= 0 {
		return fmt.Sprintf("%d * * * *", minute)
	}
	return ""
}

func readPlistInteger(body, key string) int {
	idx := strings.Index(body, "<key>"+key+"</key>")
	if idx < 0 {
		return -1
	}
	rest := body[idx:]
	openTag := strings.Index(rest, "<integer>")
	if openTag < 0 {
		return -1
	}
	rest = rest[openTag+len("<integer>"):]
	closeTag := strings.Index(rest, "</integer>")
	if closeTag < 0 {
		return -1
	}
	v := -1
	fmt.Sscanf(strings.TrimSpace(rest[:closeTag]), "%d", &v)
	return v
}

// simulateCron walks each minute in [start, end] and reports the matching
// instants. A naive approach but the windows are small (≤ 24h × 60 = 1440
// iterations) and the entry count is bounded (~25 automations max).
func simulateCron(expr string, start, end time.Time) ([]time.Time, error) {
	fields := strings.Fields(expr)
	if len(fields) < 5 {
		return nil, fmt.Errorf("invalid cron %q", expr)
	}
	min, hour, dom, mon, dow := fields[0], fields[1], fields[2], fields[3], fields[4]
	var fires []time.Time
	cur := start.Truncate(time.Minute)
	for !cur.After(end) {
		if matchField(min, cur.Minute(), 0, 59) &&
			matchField(hour, cur.Hour(), 0, 23) &&
			matchField(dom, cur.Day(), 1, 31) &&
			matchField(mon, int(cur.Month()), 1, 12) &&
			matchField(dow, int(cur.Weekday()), 0, 6) {
			if cur.After(start) {
				fires = append(fires, cur)
			}
		}
		cur = cur.Add(time.Minute)
	}
	return fires, nil
}

func matchField(spec string, value, lo, hi int) bool {
	if spec == "*" {
		return true
	}
	if strings.HasPrefix(spec, "*/") {
		var step int
		fmt.Sscanf(spec[2:], "%d", &step)
		if step <= 0 {
			return false
		}
		return (value-lo)%step == 0
	}
	for _, part := range strings.Split(spec, ",") {
		var v int
		if _, err := fmt.Sscanf(part, "%d", &v); err == nil {
			if v == value {
				return true
			}
		}
	}
	return false
}
