# Package Consolidation Design

**Date:** 2026-02-24
**Goal:** Reduce internal package count from 18 to 12 for improved navigability and reduced cognitive overhead.
**Approach:** Merge single-consumer leaf packages + absorb progress into fibonacci + add Calculate() facade.
**Correction:** `internal/ui` has 14 importers (app, cli, tui, config, calibration) — kept separate.

## Current State (18 packages)

```
internal/
  app/ bigfft/ calibration/ cli/ config/ errors/
  fibonacci/ fibonacci/memory/ fibonacci/threshold/
  format/ metrics/ orchestration/ parallel/
  progress/ sysmon/ testutil/ tui/ ui/
```

## Target State (12 packages)

```
internal/
  app/            # Lifecycle, dispatch, version (unchanged)
  bigfft/         # FFT multiplication (unchanged)
  calibration/    # Auto-calibration (unchanged)
  cli/            # CLI presentation (unchanged)
  config/         # Config parsing (unchanged)
  errors/         # Structured errors (unchanged)
  fibonacci/      # Core + memory + thresholds + progress + ErrorCollector
  format/         # Duration/number formatting (unchanged)
  metrics/        # Performance indicators (unchanged)
  orchestration/  # Concurrent execution (unchanged)
  testutil/       # Test utilities (unchanged)
  tui/            # TUI dashboard + sysmon (absorbs sysmon)
  ui/             # Colors/themes (kept — 14 importers across all layers)
```

**Eliminated:** fibonacci/memory, fibonacci/threshold, parallel, progress, sysmon

## Merge Details

### 1. fibonacci/memory → fibonacci

Move arena.go, gc_control.go, budget.go into internal/fibonacci/.
Types (CalculationArena, GCController, MemoryEstimate) have unique names — no conflicts.
Update imports in fibonacci files from `internal/fibonacci/memory` to direct references.

### 2. fibonacci/threshold → fibonacci

Move manager.go, types.go into internal/fibonacci/.
DynamicThresholdManager is uniquely named.

### 3. parallel → fibonacci

Inline ErrorCollector (~20 lines) into internal/fibonacci/common.go.
Delete internal/parallel/ entirely. Single consumer: fibonacci/common.go.

### 4. progress → fibonacci

Move progress.go, observer.go, observers.go into internal/fibonacci/.
Types: ProgressSubject, ProgressObserver, ChannelObserver, LoggingObserver, NoOpObserver, ReportStepProgress.
Delete fibonacci/progress_aliases.go (no longer needed — types are native).

Consumers and their current fibonacci dependency (no new edges):
- cli/presenter.go, cli/ui_display.go → already imports fibonacci
- tui/bridge.go → already imports fibonacci
- calibration/calibration.go → already imports fibonacci
- orchestration/orchestrator.go, orchestration/progress.go → already imports fibonacci

### 5. ~~ui → cli~~ (CANCELLED)

**Correction:** `internal/ui` has 14 importers across app, cli, tui, config, and calibration.
It serves as the shared color/theme layer and must remain a separate package.

### 6. sysmon → tui

Move sysmon.go into internal/tui/sysmon.go.
Single consumer: tui/model.go.

### 7. Facade: fibonacci.Calculate()

Add a convenience function:

```go
func Calculate(ctx context.Context, n uint64) (*big.Int, error) {
    calc := GlobalFactory().MustGet("fast")
    return calc.Calculate(ctx, nil, 0, n, Options{})
}
```

Provides a simple entry point for callers who don't need algorithm selection, progress reporting, or custom thresholds.

## Dependency Graph (After)

```
cmd/fibcalc → app
app → config, calibration, cli, tui, fibonacci, orchestration, errors
orchestration → fibonacci, errors, format
calibration → fibonacci, config, format
cli → fibonacci, config, orchestration, format, errors, metrics
tui → fibonacci, config, orchestration, format, errors, metrics
fibonacci → bigfft
bigfft, format, metrics, errors, testutil → (stdlib only)
config → errors
```

No circular dependencies. All leaf packages remain leaves.

## Implementation Order

1. fibonacci/memory → fibonacci
2. fibonacci/threshold → fibonacci
3. parallel → fibonacci
4. progress → fibonacci
5. sysmon → tui
6. Add fibonacci.Calculate() facade
7. Final validation: make test && make lint

Each step is independently verifiable with `go build ./...`.

## Testing Strategy

- `make test` after each merge (race detector enabled)
- Golden tests validate algorithm correctness
- `make lint` validates complexity thresholds
- No behavioral changes — purely structural refactoring

## Risks

- **fibonacci package size grows** by ~600 lines (10 files from 4 packages). Acceptable given the types are tightly coupled.
- **Import path churn** in progress consumers (6 files). Mechanical, low risk.
- **Test file moves** must maintain t.Parallel() and build tags.

## Not In Scope

- Performance optimizations (codebase already well-optimized)
- Merging calibration, orchestration, or format (serve distinct roles with multiple consumers)
- Merging metrics (shared by both cli and tui)
- API changes beyond the Calculate() facade
