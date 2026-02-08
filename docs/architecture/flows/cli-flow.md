# CLI Execution Flow

| Attribute | Value |
|-----------|-------|
| **Status** | Verified |
| **Type** | Execution Flow |
| **Complexity** | Medium |
| **Diagram** | [cli-flow.mermaid](cli-flow.mermaid) |

## Overview

The CLI execution flow is the default presentation mode for FibCalc. It handles configuration parsing, calculator selection, parallel execution, progress reporting (spinner + progress bar + ETA), and result presentation to stdout.

## Flow Boundaries

| Boundary | From | To |
|----------|------|----|
| Entry | `cmd/fibcalc/main.go` | `internal/app` |
| Config | `internal/config` | `internal/app` |
| Orchestration | `internal/app` | `internal/orchestration` |
| Calculation | `internal/orchestration` | `internal/fibonacci` |
| Presentation | `internal/orchestration` | `internal/cli` |

## Quick Reference

| Component | File | Line |
|-----------|------|------|
| Entry point | `cmd/fibcalc/main.go` | 18 |
| App constructor | `internal/app/app.go` | 47 |
| App runner | `internal/app/app.go` | 125 |
| Config parser | `internal/config/config.go` | 129 |
| Calculator selection | `internal/orchestration/calculator_selection.go` | 18 |
| Parallel execution | `internal/orchestration/orchestrator.go` | 56 |
| Result analysis | `internal/orchestration/orchestrator.go` | 115 |
| Progress reporter | `internal/cli/presenter.go` | 18 |

## Detailed Steps

### 1. Entry Point (`cmd/fibcalc/main.go:18`)

`main()` creates an `Application` via `app.New()` and calls `app.Run()`. The exit code from `Run()` is passed to `os.Exit()`.

### 2. Configuration (`internal/app/app.go:47`)

`app.New()` calls `config.ParseConfig()` which:
- Parses CLI flags via `flag.Parse()`
- Applies environment variable overrides (`FIBCALC_*` prefix)
- Validates the configuration
- Returns an `AppConfig` struct

### 3. Mode Dispatch (`internal/app/app.go:125`)

`app.Run()` dispatches based on configuration (priority order):
1. **Completion mode** — generates shell completion scripts
2. **Calibration mode** — runs full benchmark calibration
3. **Auto-calibrate mode** — runs quick micro-benchmarks
4. **TUI mode** — launches interactive terminal UI
5. **CLI mode** — default path (described below)

### 4. Calibration Resolution

Before calculation:
- Attempts to load a cached calibration profile from `~/.fibcalc_calibration.json`
- If no valid profile exists, runs adaptive hardware estimation (`calibration.EstimateOptimal*Threshold()`)
- Builds `fibonacci.Options` with resolved thresholds

### 5. Calculator Selection (`internal/orchestration/calculator_selection.go:18`)

`GetCalculatorsToRun()` selects calculators from `fibonacci.GlobalFactory()` based on the `--algorithm` flag. If `--compare` is set, all registered algorithms run.

### 6. Parallel Execution (`internal/orchestration/orchestrator.go:56`)

`ExecuteCalculations()`:
- **Single calculator fast path**: Calls `Calculate()` directly (no errgroup overhead)
- **Multiple calculators**: Uses `golang.org/x/sync/errgroup` to run calculators concurrently
- Each calculator creates a `ProgressSubject`, registers a `ChannelObserver`, and delegates to `CalculateWithObservers()`

### 7. Progress Reporting (`internal/cli/presenter.go:18`)

`CLIProgressReporter` consumes progress updates from the `ChannelObserver` channel:
- Displays a spinner animation (briandowns/spinner)
- Shows a progress bar with percentage
- Calculates and displays ETA
- Refreshes at 200ms intervals

### 8. Result Presentation

- **Single result**: `CLIResultPresenter.PresentResult()` formats output
- **Multiple results**: `AnalyzeComparisonResults()` (`internal/orchestration/orchestrator.go:115`) compares results, sorts by speed, then presents comparison table

### 9. Output Formatting (`internal/cli/output.go`)

Naming convention:
- `Display*`: Write formatted output to `io.Writer`
- `Format*`: Return formatted string, no I/O
- `Write*`: Write data to filesystem
- `Print*`: Write to stdout (convenience wrappers)

## Failure Scenarios

| Error | Exit Code | Handler |
|-------|-----------|---------|
| Invalid configuration | 4 (`ExitErrorConfig`) | `internal/errors/handler.go` |
| Calculation timeout | 2 (`ExitErrorTimeout`) | Context cancellation propagation |
| Result mismatch (compare mode) | 3 (`ExitErrorMismatch`) | `orchestration.AnalyzeComparisonResults` |
| User cancellation (Ctrl+C) | 130 (`ExitErrorCanceled`) | Signal handler in `app.go` |
| Generic/unexpected error | 1 (`ExitErrorGeneric`) | `internal/errors/handler.go` |

## Signal Handling

`app.Run()` sets up a signal handler for `SIGINT`/`SIGTERM` that cancels the context, propagating cancellation to all running goroutines through the `errgroup`.
