# TUI Execution Flow

| Attribute | Value |
|-----------|-------|
| **Status** | Verified |
| **Type** | Execution Flow |
| **Complexity** | High |
| **Diagram** | [tui-flow.mermaid](tui-flow.mermaid) |

## Overview

The TUI (Terminal User Interface) mode provides an interactive dashboard using the Bubble Tea framework (Elm architecture). It features real-time progress visualization, system metrics monitoring, and scrollable calculation logs.

## Flow Boundaries

| Boundary | From | To |
|----------|------|----|
| Entry | `internal/app/app.go` | `internal/tui` |
| Bridge | `internal/tui/bridge.go` | `internal/orchestration` |
| Metrics | `internal/sysmon` | `internal/tui/metrics.go` |
| Styling | `internal/ui` | `internal/tui/styles.go` |

## Quick Reference

| Component | File | Line |
|-----------|------|------|
| Model struct | `internal/tui/model.go` | 22 |
| TUI progress reporter | `internal/tui/bridge.go` | 32 |
| TUI result presenter | `internal/tui/bridge.go` | 64 |
| Header panel | `internal/tui/header.go` | — |
| Footer panel | `internal/tui/footer.go` | — |
| Logs panel | `internal/tui/logs.go` | — |
| Metrics panel | `internal/tui/metrics.go` | — |
| Chart panel | `internal/tui/chart.go` | — |
| Styles | `internal/tui/styles.go` | — |
| Key bindings | `internal/tui/keymap.go` | — |
| Messages | `internal/tui/messages.go` | — |

## Detailed Steps

### 1. TUI Initialization

When `--tui` flag is set, `app.Run()` creates a Bubble Tea program:
- Creates `TUIProgressReporter` and `TUIResultPresenter` bridge adapters
- Initializes the `Model` struct with config, bridges, and initial state
- Launches `tea.NewProgram(model)` with alt-screen mode

### 2. Model.Init (`internal/tui/model.go`)

The `Init()` method returns three initial commands:
- `tickCmd` — 500ms periodic tick for metric updates
- `startCalculationCmd` — triggers background calculation goroutine
- `watchContextCmd` — monitors context cancellation

### 3. Bridge Pattern (`internal/tui/bridge.go`)

The bridge layer adapts orchestration interfaces to Bubble Tea messages:

**`TUIProgressReporter`** (line 32):
- Implements `orchestration.ProgressReporter`
- Uses `programRef` pattern — stores `*tea.Program` pointer that survives Bubble Tea's value-copy semantics
- Calls `program.Send()` to inject `ProgressMsg` into the Bubble Tea event loop

**`TUIResultPresenter`** (line 64):
- Implements `orchestration.ResultPresenter`
- Sends `FinalResultMsg`, `ComparisonResultsMsg`, or `ErrorMsg` via `program.Send()`

### 4. Message Types (`internal/tui/messages.go`)

| Message | Source | Purpose |
|---------|--------|---------|
| `ProgressMsg` | Bridge | Progress update from calculator |
| `ComparisonResultsMsg` | Bridge | Multi-algorithm comparison results |
| `FinalResultMsg` | Bridge | Single algorithm result |
| `ErrorMsg` | Bridge | Calculation error |
| `CalculationCompleteMsg` | Background goroutine | Signals all calculations done |
| `TickMsg` | tickCmd (500ms) | Periodic refresh trigger |
| `MemStatsMsg` | Tick handler | Runtime memory statistics |
| `SysStatsMsg` | Tick handler | System CPU/memory from gopsutil |
| `IndicatorsMsg` | Tick handler | Performance indicators |
| `ContextCancelledMsg` | watchContextCmd | Context cancellation notification |

### 5. Model.Update (Elm Architecture)

The `Update()` method processes messages immutably:
- **Generation guard**: Each calculation has a generation counter. Messages from stale generations (after restart) are rejected.
- State transitions are pure — the model is updated and new commands are returned.
- Side effects happen only through Bubble Tea commands.

### 6. Model.View (Panel Layout)

The `View()` method renders five panels:

```
┌──────────────────────────────────────┐
│ Header: Title + Elapsed Time    (1r) │
├────────────────────┬─────────────────┤
│                    │ Metrics    (7r) │
│ Logs        (60%)  ├─────────────────┤
│                    │ Chart   (rest)  │
├────────────────────┴─────────────────┤
│ Footer: Key Bindings + Status   (1r) │
└──────────────────────────────────────┘
```

- **Header** (`header.go`): Title, algorithm name, elapsed time
- **Footer** (`footer.go`): Key bindings help, status indicators
- **Logs** (`logs.go`): 60% of width, scrollable calculation log
- **Metrics** (`metrics.go`): 7 rows, right side — memory usage, GC stats, goroutine count
- **Chart** (`chart.go`): Remaining right side — progress sparkline visualization

### 7. Key Bindings (`internal/tui/keymap.go`)

| Key | Action |
|-----|--------|
| `q` / `Ctrl+C` | Quit application |
| `Space` | Pause/Resume calculation |
| `r` | Restart calculation (increments generation) |
| `Up`/`Down` | Scroll log panel |

## Failure Scenarios

| Error | Handling |
|-------|----------|
| Calculation error | `ErrorMsg` displayed in logs panel, footer shows error state |
| Context timeout | `ContextCancelledMsg` triggers graceful shutdown |
| User quit (q/Ctrl+C) | `tea.Quit` command, cleanup in model teardown |
| Bridge send after quit | `programRef` nil check prevents panics |

## Architectural Notes

- The `programRef` pattern is critical: Bubble Tea copies the model by value, so a direct `*tea.Program` field would be stale after updates. The bridge stores the pointer in a shared reference object.
- The generation guard prevents message races when the user restarts a calculation — stale messages from the previous run are silently dropped.
- Lipgloss styles are defined in `styles.go` with `NO_COLOR` support via `internal/ui/colors.go`.
