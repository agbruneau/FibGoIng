# CLI-Only Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the HTTP server, TUI, REPL, and all observability layers (Prometheus, OpenTelemetry) to produce a pure one-shot CLI application, preserving all Fibonacci algorithms.

**Architecture:** The app keeps its clean layered structure (Entry Point → Orchestration → Business → Presentation) but presentation is now CLI-only. The server, service, TUI packages are deleted entirely. Prometheus/OTel instrumentation is removed from the fibonacci core. The REPL is removed from the CLI package.

**Tech Stack:** Go 1.25+, zerolog, golang.org/x/sync, spinner. Removed: Prometheus, OpenTelemetry, Bubbletea/Bubbles/Lipgloss.

---

### Task 1: Delete isolated packages (server, service, TUI)

These packages are only imported by each other or by `app.go` — nothing else depends on them.

**Files:**
- Delete: `internal/server/` (entire directory — all `.go` files and tests)
- Delete: `internal/service/` (entire directory — `calculator_service.go`, `calculator_service_test.go`, `mocks/`)
- Delete: `internal/tui/` (entire directory — all `.go` files)

**Step 1: Delete internal/server/**

```bash
rm -rf internal/server/
```

**Step 2: Delete internal/service/**

```bash
rm -rf internal/service/
```

**Step 3: Delete internal/tui/**

```bash
rm -rf internal/tui/
```

**Step 4: Delete internal/cli/repl.go and its test**

```bash
rm internal/cli/repl.go internal/cli/repl_test.go
```

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: delete server, service, TUI, REPL packages"
```

---

### Task 2: Remove server/TUI/REPL routing from app.go

**Files:**
- Modify: `internal/app/app.go:3-24` (imports), `internal/app/app.go:127-203` (Run + removed methods)

**Step 1: Update imports**

Remove these import lines from `internal/app/app.go`:

```go
// REMOVE these lines:
"github.com/agbru/fibcalc/internal/server"
"github.com/agbru/fibcalc/internal/tui"
```

**Step 2: Remove server/TUI/REPL dispatch from Run()**

In `internal/app/app.go`, remove lines 140-153 from `Run()`:

```go
// REMOVE this block:
// Server mode
if a.Config.ServerMode {
    return a.runServer()
}

// TUI mode
if a.Config.TUIMode {
    return a.runTUI()
}

// Interactive REPL mode
if a.Config.Interactive {
    return a.runREPL()
}
```

Also remove the comment on lines 133-134 about server mode overriding logging:
```go
// REMOVE:
// Disable trace-level logging by default to avoid polluting CLI output.
// Server mode may override this to enable more verbose logging.
```
Keep the `zerolog.SetGlobalLevel(zerolog.InfoLevel)` line itself.

**Step 3: Remove runServer(), runREPL(), runTUI() methods**

Delete these methods entirely from `internal/app/app.go`:

- `runServer()` (lines 177-185)
- `runREPL()` (lines 187-198)
- `runTUI()` (lines 200-203)

**Step 4: Update Application struct docstring**

In `internal/app/app.go:26-28`, change:

```go
// Application represents the fibcalc application instance.
// It encapsulates the configuration and provides methods to run
// the application in various modes (CLI, server, REPL).
```

to:

```go
// Application represents the fibcalc application instance.
// It encapsulates the configuration and provides methods to run
// the application in CLI mode.
```

**Step 5: Verify compilation**

```bash
go build ./internal/app/
```

Expected: SUCCESS (no errors)

**Step 6: Commit**

```bash
git add internal/app/app.go
git commit -m "refactor(app): remove server, TUI, REPL routing from application"
```

---

### Task 3: Remove server/TUI/REPL/interactive tests from app_test.go

**Files:**
- Modify: `internal/app/app_test.go`

**Step 1: Remove TestRunServer (lines 648-694)**

Delete the entire `TestRunServer` function.

**Step 2: Remove TestRunREPL (lines 696-727)**

Delete the entire `TestRunREPL` function.

**Step 3: Remove server/REPL modes from TestRunAllModes (lines 910-993)**

Delete the "Server mode" subtest (lines 914-942) and the "REPL mode" subtest (lines 944-964). Keep the "Calibration mode" subtest.

**Step 4: Verify tests pass**

```bash
go test -v -run TestRunAllModes ./internal/app/
```

Expected: PASS (only "Calibration mode" subtest runs)

**Step 5: Commit**

```bash
git add internal/app/app_test.go
git commit -m "test(app): remove server, TUI, REPL test cases"
```

---

### Task 4: Clean config — remove ServerMode, Port, TUIMode, Interactive

**Files:**
- Modify: `internal/config/config.go:47-103` (struct), `internal/config/config.go:168-220` (ParseConfig)
- Modify: `internal/config/env.go:149-198` (env overrides)

**Step 1: Remove fields from AppConfig struct**

In `internal/config/config.go`, delete these fields and their comments:

```go
// ServerMode, if true, starts the application as an HTTP server.
ServerMode bool
// Port specifies the port to listen on in server mode.
Port string
```

```go
// Interactive, if true, starts the application in REPL mode.
Interactive bool
```

```go
// TUIMode, if true, starts the application in interactive TUI mode.
// The TUI provides a rich terminal interface with navigation, progress bars,
// and interactive algorithm selection.
TUIMode bool
```

**Step 2: Remove DefaultPort constant**

In `internal/config/config.go`, delete:

```go
// DefaultPort is the default server port.
DefaultPort = "8080"
```

**Step 3: Remove flag definitions from ParseConfig()**

In `internal/config/config.go`, delete these lines from `ParseConfig()`:

```go
fs.BoolVar(&config.ServerMode, "server", false, "Start in HTTP server mode.")
fs.StringVar(&config.Port, "port", DefaultPort, "Port to listen on in server mode.")
fs.BoolVar(&config.Interactive, "interactive", false, "Start in interactive REPL mode.")
fs.BoolVar(&config.TUIMode, "tui", false, "Start in interactive TUI mode with rich terminal interface.")
```

**Step 4: Remove env overrides for removed fields**

In `internal/config/env.go`:

Delete from `applyStringOverrides()`:
```go
if !isFlagSet(fs, "port") {
    config.Port = getEnvString("PORT", config.Port)
}
```

Delete from `applyBooleanOverrides()`:
```go
if !isFlagSet(fs, "server") {
    config.ServerMode = getEnvBool("SERVER", config.ServerMode)
}
```

```go
if !isFlagSet(fs, "interactive") {
    config.Interactive = getEnvBool("INTERACTIVE", config.Interactive)
}
```

Also remove from the `applyEnvOverrides` docstring: references to `FIBCALC_SERVER`, `FIBCALC_PORT`, `FIBCALC_INTERACTIVE`.

**Step 5: Verify compilation**

```bash
go build ./internal/config/
```

Expected: SUCCESS

**Step 6: Commit**

```bash
git add internal/config/config.go internal/config/env.go
git commit -m "refactor(config): remove server, port, interactive, TUI flags and env vars"
```

---

### Task 5: Fix config tests

**Files:**
- Modify: `internal/config/config_test.go`
- Modify: `internal/config/config_exhaustive_test.go`
- Modify: `internal/config/config_extra_test.go`

**Step 1: Fix config_test.go**

In `TestParseConfig`'s "ValidFlags" subtest:
- Remove `-server` and `-port 9090` from the args slice
- Remove assertions for `cfg.ServerMode` and `cfg.Port`

In `TestParseConfig`'s "EnvOverrides" subtest:
- Remove `FIBCALC_SERVER`, `FIBCALC_PORT`, `FIBCALC_INTERACTIVE` env var setups
- Remove assertions for `cfg.ServerMode`, `cfg.Port`, `cfg.Interactive`

**Step 2: Fix config_exhaustive_test.go**

In `TestParseConfigDefaults`:
- Remove assertions for `cfg.ServerMode` default (false) and `cfg.Port` default ("8080")

In `TestParseConfigAllFlags`:
- Remove `-server` and `-port 9090` from args
- Remove assertions for `cfg.ServerMode` and `cfg.Port`

**Step 3: Fix config_extra_test.go**

In `TestParseConfigEnvironmentVariables`:
- Remove `FIBCALC_PORT` and `FIBCALC_SERVER` env var setup
- Remove assertions for `cfg.Port` and `cfg.ServerMode`

**Step 4: Run config tests**

```bash
go test -v ./internal/config/
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add internal/config/config_test.go internal/config/config_exhaustive_test.go internal/config/config_extra_test.go
git commit -m "test(config): remove server, port, interactive, TUI test assertions"
```

---

### Task 6: Remove Prometheus and OpenTelemetry from fibonacci core

**Files:**
- Modify: `internal/fibonacci/calculator.go:10-43` (imports + metrics vars), `internal/fibonacci/calculator.go:164-186` (CalculateWithObservers)
- Modify: `internal/fibonacci/observers.go` (remove MetricsObserver section)
- Modify: `internal/fibonacci/observer_test.go` (remove MetricsObserver tests)

**Step 1: Remove Prometheus imports and global metrics from calculator.go**

In `internal/fibonacci/calculator.go`, remove these imports:
```go
"github.com/prometheus/client_golang/prometheus"
"github.com/prometheus/client_golang/prometheus/promauto"
"go.opentelemetry.io/otel"
```

Delete the global metrics variables (lines 28-43):
```go
var (
    calculationsTotal = promauto.NewCounterVec(...)
    calculationDuration = promauto.NewHistogramVec(...)
)
```

**Step 2: Simplify CalculateWithObservers — remove OTel tracer and Prometheus recording**

Replace the current `CalculateWithObservers` method body (lines 164-212). Remove the OTel tracer/span and the Prometheus recording in the defer. Keep the zerolog trace log. The new body:

```go
func (c *FibCalculator) CalculateWithObservers(ctx context.Context, subject *ProgressSubject, calcIndex int, n uint64, opts Options) (result *big.Int, err error) {
	start := time.Now()
	defer func() {
		duration := time.Since(start).Seconds()
		status := "success"
		if err != nil {
			status = "error"
		}
		log.Trace().
			Str("algo", c.core.Name()).
			Uint64("n", n).
			Float64("duration", duration).
			Str("status", status).
			Msg("calculation completed")
	}()

	// Create a reporter that notifies all observers
	var reporter ProgressReporter
	if subject != nil {
		reporter = subject.AsProgressReporter(calcIndex)
	} else {
		reporter = func(float64) {} // No-op reporter
	}

	if n <= MaxFibUint64 {
		reporter(1.0)
		return calculateSmall(n), nil
	}

	// Configure FFT cache based on options for optimal performance
	configureFFTCache(opts)

	// Pre-warm pools once for large calculations (one-time initialization)
	bigfft.EnsurePoolsWarmed(n)

	result, err = c.core.CalculateCore(ctx, reporter, n, opts)
	if err == nil && result != nil {
		reporter(1.0)
	}
	return result, err
}
```

**Step 3: Remove MetricsObserver from observers.go**

In `internal/fibonacci/observers.go`:

- Remove Prometheus imports (`"github.com/prometheus/client_golang/prometheus"` and `"github.com/prometheus/client_golang/prometheus/promauto"`)
- Delete the entire "Metrics Observer (Prometheus)" section (lines 122-167): the `progressGauge` var, `MetricsObserver` struct, `NewMetricsObserver()`, `Update()`, and `ResetMetrics()` methods

**Step 4: Remove MetricsObserver tests from observer_test.go**

In `internal/fibonacci/observer_test.go`:

- Delete `TestMetricsObserver_Update` (lines 356-365)
- Delete `TestMetricsObserver_ResetMetrics` (lines 368-375)
- In `TestMultipleObserversIntegration` (line 396-439): remove the MetricsObserver setup. Delete these lines:
  ```go
  // Set up metrics observer
  metricsObs := NewMetricsObserver()
  ```
  and:
  ```go
  subject.Register(metricsObs)
  ```

**Step 5: Verify compilation and tests**

```bash
go build ./internal/fibonacci/ && go test -v ./internal/fibonacci/ -run TestMetrics -run TestMultipleObservers
```

Expected: Build succeeds. TestMetrics tests are gone (no match). TestMultipleObserversIntegration passes.

**Step 6: Commit**

```bash
git add internal/fibonacci/calculator.go internal/fibonacci/observers.go internal/fibonacci/observer_test.go
git commit -m "refactor(fibonacci): remove Prometheus metrics and OpenTelemetry tracing"
```

---

### Task 7: Clean shell completion scripts

**Files:**
- Modify: `internal/cli/completion.go`

**Step 1: Remove server/port/interactive/TUI flags from all 4 completion generators**

In `generateBashCompletion()` (line 45): Remove `--server --port --interactive` from the `opts` string.

In `generateBashCompletion()` (lines 64-66): Delete the `--port` case block:
```bash
--port)
    COMPREPLY=( $(compgen -W "8080 3000 5000 9000" -- "${cur}") )
    return 0
    ;;
```

In `generateZshCompletion()` (lines 124-125): Delete these lines:
```
'--server[Start HTTP server mode]' \
'--port[Server port]:port:(8080 3000 5000 9000)' \
```

And delete:
```
'--interactive[Start interactive REPL mode]' \
```

In `generateFishCompletion()` (lines 183-188): Delete:
```bash
# Server mode
complete -c fibcalc -l server -d 'Start HTTP server mode'
complete -c fibcalc -l port -d 'Server port' -xa '8080 3000 5000 9000'

# Interactive and completion
complete -c fibcalc -l interactive -d 'Start interactive REPL mode'
```

Rename the remaining comment to just `# Completion`:
```bash
# Completion
complete -c fibcalc -l completion -d 'Generate completion script' -xa 'bash zsh fish powershell'
```

In `generatePowerShellCompletion()` (lines 230-232, 238, 266-271): Delete:
```powershell
@{Name = '--server'; Description = 'Start HTTP server mode' }
@{Name = '--port'; Description = 'Server port' }
@{Name = '--interactive'; Description = 'Start interactive REPL mode' }
```

And delete the `--port` case in the switch:
```powershell
'--port' {
    @('8080', '3000', '5000', '9000') | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
    return
}
```

**Step 2: Verify compilation**

```bash
go build ./internal/cli/
```

Expected: SUCCESS

**Step 3: Commit**

```bash
git add internal/cli/completion.go
git commit -m "refactor(cli): remove server, port, interactive flags from shell completions"
```

---

### Task 8: Clean ancillary files (Makefile, .env.example, docs, Dockerfile)

**Files:**
- Modify: `Makefile`
- Modify: `.env.example`
- Delete: `Dockerfile`
- Delete: `Docs/api/` (entire directory — API.md, openapi.yaml, postman_collection.json)
- Delete: `Docs/deployment/` (entire directory — DOCKER.md, KUBERNETES.md)
- Delete: `Docs/MONITORING.md`
- Delete: `Docs/SECURITY.md` (if server-specific; check first)

**Step 1: Clean Makefile**

Delete the `run-server` target (lines 172-174):
```makefile
## run-server: Run in server mode
run-server: build
	$(BUILD_DIR)/$(BINARY_NAME) --server --port 8080
```

Delete the `docker-build` and `docker-run` targets (lines 233-241):
```makefile
## docker-build: Build Docker image
docker-build:
	...
## docker-run: Run Docker container
docker-run:
	...
```

**Step 2: Clean .env.example**

Delete the "HTTP Server Configuration" section (lines 34-46):
```
# =============================================================================
# HTTP Server Configuration
# =============================================================================
...
FIBCALC_SERVER=false
FIBCALC_PORT=8080
```

Delete the "REPL interactive mode" entry (lines 133-136):
```
# Enable REPL interactive mode
...
FIBCALC_INTERACTIVE=false
```

**Step 3: Delete server-specific docs and Dockerfile**

```bash
rm Dockerfile
rm -rf Docs/api/
rm -rf Docs/deployment/
rm Docs/MONITORING.md
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove server-related Makefile targets, env config, docs, and Dockerfile"
```

---

### Task 9: Run go mod tidy and full verification

**Files:**
- Modify: `go.mod`, `go.sum` (via go mod tidy)

**Step 1: Run go mod tidy**

```bash
go mod tidy
```

Expected: Removes `prometheus/client_golang`, `go.opentelemetry.io/otel`, `charmbracelet/bubbletea`, `charmbracelet/bubbles`, `charmbracelet/lipgloss` and their transitive deps.

**Step 2: Verify build**

```bash
go build ./...
```

Expected: SUCCESS (no errors)

**Step 3: Run all tests**

```bash
go test -race ./...
```

Expected: ALL PASS. No compilation errors from removed packages.

**Step 4: Verify CLI help**

```bash
go run ./cmd/fibcalc -h
```

Expected: Help output shows NO `--server`, `--port`, `--interactive`, `--tui` flags.

**Step 5: Commit**

```bash
git add go.mod go.sum
git commit -m "chore: go mod tidy — remove unused server/TUI/observability dependencies"
```

---

### Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Update these sections:

- **Build & Test Commands**: Remove `make run-server` if listed.
- **Architecture Overview**: Remove "Server" from entry points. Remove "HTTP API" from presentation layer. Update to say CLI-only.
- **Core Packages table**: Remove `internal/server`, `internal/service`, `internal/tui` rows. Remove TUI-related entries.
- **Key Dependencies**: Remove `prometheus/client_golang`, `go.opentelemetry.io/otel`. Remove TUI dependencies section.
- **Naming Conventions**: Remove TUI package section.
- **Adding New Components**: Remove "New API Endpoint" section.
- **Observer Pattern**: Remove mention of `MetricsObserver`.
- **Build Tags**: Keep as-is (GMP, amd64, PGO are still relevant).

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect CLI-only architecture"
```

---

## Dependency Graph

```
Task 1 (delete packages)
  └─► Task 2 (fix app.go imports/routing)
       └─► Task 3 (fix app_test.go)
Task 4 (clean config) — can run in parallel with Task 2
  └─► Task 5 (fix config tests)
Task 6 (clean fibonacci core) — can run in parallel with Task 2
Task 7 (clean completions) — can run in parallel with Task 4
Task 8 (clean ancillary) — can run in parallel with Task 4
Task 9 (go mod tidy + verify) — depends on ALL above
Task 10 (update CLAUDE.md) — depends on Task 9
```

## Estimated Scope

- **Files deleted**: ~35 files across `internal/server/`, `internal/service/`, `internal/tui/`, `internal/cli/repl.go`, `Docs/api/`, `Docs/deployment/`, `Dockerfile`
- **Files modified**: ~12 files (`app.go`, `app_test.go`, `config.go`, `env.go`, 3 config test files, `calculator.go`, `observers.go`, `observer_test.go`, `completion.go`, `Makefile`, `.env.example`, `CLAUDE.md`)
- **Dependencies removed**: Prometheus, OpenTelemetry, Bubbletea, Bubbles, Lipgloss + transitive deps
- **Risk**: Low — server/TUI/service layers are cleanly isolated
