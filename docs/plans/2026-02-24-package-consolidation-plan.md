# Package Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce internal package count from 18 to 12 by merging single-consumer leaf packages into their consumers and absorbing progress into fibonacci.

**Architecture:** Each merge is a standalone commit: move files, change `package` declarations, update import paths, delete the old package directory. No behavioral changes — purely structural.

**Tech Stack:** Go 1.25+, `make test` (race detector), `make lint` (golangci-lint)

**Design doc:** `docs/plans/2026-02-24-package-consolidation-design.md`

---

### Task 1: Merge fibonacci/memory into fibonacci

**Files:**
- Move: `internal/fibonacci/memory/arena.go` → `internal/fibonacci/arena.go`
- Move: `internal/fibonacci/memory/budget.go` → `internal/fibonacci/budget.go`
- Move: `internal/fibonacci/memory/gc_control.go` → `internal/fibonacci/gc_control.go`
- Move: `internal/fibonacci/memory/arena_test.go` → `internal/fibonacci/arena_test.go`
- Move: `internal/fibonacci/memory/budget_test.go` → `internal/fibonacci/budget_test.go`
- Move: `internal/fibonacci/memory/gc_control_test.go` → `internal/fibonacci/gc_control_test.go`
- Modify: `internal/fibonacci/calculator.go` (remove `memory` import, use types directly)
- Modify: `internal/fibonacci/fastdoubling.go` (remove `memory` import)
- Modify: `internal/fibonacci/fft_based.go` (remove `memory` import)
- Modify: `internal/app/calculate.go` (change import from `internal/fibonacci/memory` to `internal/fibonacci`)
- Delete: `internal/fibonacci/memory/` directory

**Step 1: Move source files and change package declarations**

For each of the 6 files in `internal/fibonacci/memory/`:
1. Copy to `internal/fibonacci/` with the same filename
2. Change `package memory` to `package fibonacci`
3. Remove the old file

**Step 2: Update imports in consumers**

In `internal/fibonacci/calculator.go`, remove:
```go
"github.com/agbru/fibcalc/internal/fibonacci/memory"
```
And change `memory.NewGCController` → `NewGCController`, `memory.GCController` → `GCController`.

In `internal/fibonacci/fastdoubling.go`, remove:
```go
"github.com/agbru/fibcalc/internal/fibonacci/memory"
```
And change `memory.NewCalculationArena` → `NewCalculationArena`, `memory.CalculationArena` → `CalculationArena`.

In `internal/fibonacci/fft_based.go`, same pattern.

In `internal/app/calculate.go`, change:
```go
"github.com/agbru/fibcalc/internal/fibonacci/memory"
```
to:
```go
"github.com/agbru/fibcalc/internal/fibonacci"
```
And prefix any `memory.X` references with `fibonacci.X`.

**Step 3: Delete the old directory**

```bash
rm -rf internal/fibonacci/memory/
```

**Step 4: Verify build**

```bash
go build ./...
```
Expected: no errors.

**Step 5: Run tests**

```bash
go test -race -short ./internal/fibonacci/... ./internal/app/...
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add -A internal/fibonacci/ internal/app/calculate.go
git commit -m "refactor: merge fibonacci/memory into fibonacci package"
```

---

### Task 2: Merge fibonacci/threshold into fibonacci

**Files:**
- Move: `internal/fibonacci/threshold/manager.go` → `internal/fibonacci/threshold_manager.go`
- Move: `internal/fibonacci/threshold/types.go` → `internal/fibonacci/threshold_types.go`
- Move: `internal/fibonacci/threshold/manager_test.go` → `internal/fibonacci/threshold_manager_test.go`
- Modify: `internal/fibonacci/fastdoubling.go` (remove `threshold` import)
- Modify: `internal/fibonacci/doubling_framework.go` (remove `threshold` import)
- Modify: `internal/fibonacci/doubling_framework_test.go` (remove `threshold` import)
- Delete: `internal/fibonacci/threshold/` directory

**Step 1: Move files, change package declarations**

For each file in `internal/fibonacci/threshold/`:
1. Copy to `internal/fibonacci/` (prefix filenames with `threshold_` to avoid conflicts)
2. Change `package threshold` to `package fibonacci`

**Step 2: Update imports in consumers**

In `internal/fibonacci/fastdoubling.go` and `internal/fibonacci/doubling_framework.go`, remove:
```go
"github.com/agbru/fibcalc/internal/fibonacci/threshold"
```
And change `threshold.DynamicThresholdManager` → `DynamicThresholdManager`, etc.

Same for `doubling_framework_test.go`.

**Step 3: Delete old directory**

```bash
rm -rf internal/fibonacci/threshold/
```

**Step 4: Verify build**

```bash
go build ./...
```

**Step 5: Run tests**

```bash
go test -race -short ./internal/fibonacci/...
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add -A internal/fibonacci/
git commit -m "refactor: merge fibonacci/threshold into fibonacci package"
```

---

### Task 3: Merge parallel into fibonacci

**Files:**
- Modify: `internal/fibonacci/common.go` (inline ErrorCollector, remove `parallel` import)
- Create: `internal/fibonacci/error_collector.go` (extracted from parallel/errors.go)
- Create: `internal/fibonacci/error_collector_test.go` (from parallel/errors_test.go)
- Delete: `internal/parallel/` directory

**Step 1: Create error_collector.go in fibonacci**

Create `internal/fibonacci/error_collector.go` with content from `internal/parallel/errors.go`, changing `package parallel` to `package fibonacci`:

```go
package fibonacci

import "sync"

// ErrorCollector collects the first error from parallel goroutines.
// It is thread-safe and can be used by multiple goroutines simultaneously.
type ErrorCollector struct {
	once sync.Once
	err  error
}

// SetError records an error if one hasn't been recorded yet.
// Nil errors are ignored. This method is thread-safe.
func (c *ErrorCollector) SetError(err error) {
	if err != nil {
		c.once.Do(func() {
			c.err = err
		})
	}
}

// Err returns the first recorded error, or nil if no error was recorded.
func (c *ErrorCollector) Err() error {
	return c.err
}

// Reset resets the collector for reuse.
// WARNING: This is NOT thread-safe and should only be called when
// no goroutines are using the collector.
func (c *ErrorCollector) Reset() {
	c.once = sync.Once{}
	c.err = nil
}
```

**Step 2: Create error_collector_test.go**

Copy `internal/parallel/errors_test.go` to `internal/fibonacci/error_collector_test.go`, change `package parallel` to `package fibonacci`.

**Step 3: Update common.go**

In `internal/fibonacci/common.go`, remove:
```go
"github.com/agbru/fibcalc/internal/parallel"
```
And change `parallel.ErrorCollector` → `ErrorCollector` (3 occurrences: lines 98, 181, 229).

**Step 4: Delete old directory**

```bash
rm -rf internal/parallel/
```

**Step 5: Verify build**

```bash
go build ./...
```

**Step 6: Run tests**

```bash
go test -race -short ./internal/fibonacci/...
```
Expected: all PASS.

**Step 7: Commit**

```bash
git add -A internal/fibonacci/ && git add -A internal/parallel/
git commit -m "refactor: merge parallel/ErrorCollector into fibonacci package"
```

---

### Task 4: Merge progress into fibonacci

This is the largest merge — 16 files import `internal/progress`.

**Files:**
- Move: `internal/progress/progress.go` → `internal/fibonacci/progress.go`
- Move: `internal/progress/observer.go` → `internal/fibonacci/progress_observer.go`
- Move: `internal/progress/observers.go` → `internal/fibonacci/progress_observers.go`
- Move: `internal/progress/progress_test.go` → `internal/fibonacci/progress_reporting_test.go`
- Move: `internal/progress/observer_test.go` → `internal/fibonacci/progress_observer_test.go`
- Delete: `internal/fibonacci/progress_aliases.go` (types are now native)
- Modify (import path change, `progress.X` → `fibonacci.X`):
  - `internal/orchestration/orchestrator.go`
  - `internal/orchestration/progress.go`
  - `internal/orchestration/interfaces.go`
  - `internal/orchestration/orchestrator_test.go`
  - `internal/orchestration/progress_test.go`
  - `internal/orchestration/orchestration_spy_test.go`
  - `internal/cli/presenter.go`
  - `internal/cli/ui_display.go`
  - `internal/cli/ui_test.go`
  - `internal/cli/ui_advanced_test.go`
  - `internal/tui/bridge.go`
  - `internal/tui/bridge_test.go`
  - `internal/calibration/calibration.go`
  - `internal/calibration/calibration_test.go`
  - `internal/calibration/calibration_advanced_test.go`
- Delete: `internal/progress/` directory

**Step 1: Move source files, change package declarations**

For the 3 source files and 2 test files:
1. Copy to `internal/fibonacci/` with the renamed filenames above (to avoid conflict with existing `progress_aliases.go` — which we'll delete)
2. Change `package progress` to `package fibonacci`

Note: `progress.go` in the progress package contains types `ProgressUpdate`, `ProgressCallback`, `CalcTotalWork`, `PrecomputePowers4`, `ReportStepProgress`. These are already re-exported via `progress_aliases.go` in fibonacci — so consumers using `fibonacci.ProgressUpdate` continue to work without changes. Consumers using `progress.ProgressUpdate` need updating.

**Step 2: Delete progress_aliases.go**

Delete `internal/fibonacci/progress_aliases.go` — its purpose was to bridge the now-eliminated gap.

**Step 3: Update all consumer imports**

For each of the ~15 files listed above:
1. Remove `"github.com/agbru/fibcalc/internal/progress"` from imports
2. Add `"github.com/agbru/fibcalc/internal/fibonacci"` if not already present
3. Change all `progress.X` references to `fibonacci.X`

Example for `internal/orchestration/orchestrator.go`:
- Remove: `"github.com/agbru/fibcalc/internal/progress"`
- Already has: `"github.com/agbru/fibcalc/internal/fibonacci"` (verify)
- Change: `progress.ProgressUpdate` → `fibonacci.ProgressUpdate`
- Change: `progress.NewChannelObserver` → `fibonacci.NewChannelObserver`
- etc.

**Step 4: Delete old directory**

```bash
rm -rf internal/progress/
```

**Step 5: Verify build**

```bash
go build ./...
```

**Step 6: Run tests**

```bash
go test -race -short ./...
```
Expected: all PASS. Run the full suite since this merge touches many packages.

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: merge progress into fibonacci package

Absorbs progress types (ProgressUpdate, ProgressSubject, observers)
into fibonacci. Removes progress_aliases.go (now unnecessary).
Updates 15 consumer files across orchestration, cli, tui, calibration."
```

---

### Task 5: Merge sysmon into tui

**Files:**
- Move: `internal/sysmon/sysmon.go` → `internal/tui/sysmon.go`
- Move: `internal/sysmon/sysmon_test.go` → `internal/tui/sysmon_test.go`
- Modify: `internal/tui/model.go` (remove `sysmon` import, use types directly)
- Delete: `internal/sysmon/` directory

**Step 1: Move files, change package declarations**

Copy the 2 sysmon files to `internal/tui/`, change `package sysmon` to `package tui`.
Rename exported types if needed: `Stats` → `SysmonStats` (to avoid collision with any existing `Stats` in tui). Check if `Stats` name conflicts exist first.

**Step 2: Update imports in tui/model.go**

Remove:
```go
"github.com/agbru/fibcalc/internal/sysmon"
```
Change `sysmon.Sample()` → `sysmonSample()` or `SysmonSample()` (make `Sample` unexported since it's now package-internal). Change `sysmon.Stats` → `SysmonStats` or just `Stats`.

**Step 3: Delete old directory**

```bash
rm -rf internal/sysmon/
```

**Step 4: Verify build**

```bash
go build ./...
```

**Step 5: Run tests**

```bash
go test -race -short ./internal/tui/...
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add -A internal/tui/ internal/sysmon/
git commit -m "refactor: merge sysmon into tui package"
```

---

### Task 6: Add fibonacci.Calculate() facade

**Files:**
- Create: `internal/fibonacci/calculate.go`
- Create: `internal/fibonacci/calculate_test.go`

**Step 1: Write the failing test**

Create `internal/fibonacci/calculate_test.go`:

```go
package fibonacci

import (
	"context"
	"math/big"
	"testing"
)

func TestCalculate(t *testing.T) {
	t.Parallel()
	tests := []struct {
		n    uint64
		want string
	}{
		{0, "0"},
		{1, "1"},
		{10, "55"},
		{50, "12586269025"},
	}
	for _, tt := range tests {
		t.Run(fmt.Sprintf("n=%d", tt.n), func(t *testing.T) {
			t.Parallel()
			result, err := Calculate(context.Background(), tt.n)
			if err != nil {
				t.Fatalf("Calculate(%d) error: %v", tt.n, err)
			}
			if result.String() != tt.want {
				t.Errorf("Calculate(%d) = %s, want %s", tt.n, result.String(), tt.want)
			}
		})
	}
}
```

**Step 2: Run test to verify it fails**

```bash
go test ./internal/fibonacci/ -run TestCalculate -v
```
Expected: FAIL — `Calculate` not defined.

**Step 3: Write implementation**

Create `internal/fibonacci/calculate.go`:

```go
package fibonacci

import (
	"context"
	"math/big"
)

// Calculate computes the n-th Fibonacci number using the default Fast Doubling
// algorithm with default options. This is a convenience facade for callers who
// don't need algorithm selection, progress reporting, or custom thresholds.
func Calculate(ctx context.Context, n uint64) (*big.Int, error) {
	calc := GlobalFactory().MustGet("fast")
	return calc.Calculate(ctx, nil, 0, n, Options{})
}
```

**Step 4: Run test to verify it passes**

```bash
go test ./internal/fibonacci/ -run TestCalculate -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add internal/fibonacci/calculate.go internal/fibonacci/calculate_test.go
git commit -m "feat: add fibonacci.Calculate() convenience facade"
```

---

### Task 7: Final validation

**Step 1: Full test suite with race detector**

```bash
make test
```
Expected: all PASS.

**Step 2: Lint**

```bash
make lint
```
Expected: no errors.

**Step 3: Build all platforms**

```bash
go build ./...
```
Expected: success.

**Step 4: Verify package count**

```bash
find internal/ -name "*.go" -not -path "*_test.go" | xargs grep -l "^package " | sed 's|/[^/]*$||' | sort -u | wc -l
```
Expected: 12 unique package directories.

**Step 5: Final commit (design doc update)**

```bash
git add docs/plans/
git commit -m "docs: update design doc with ui correction (18→12 packages)"
```
