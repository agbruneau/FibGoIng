# FibGo Enterprise Readiness — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise FibGo from "prototype mature" (8.6/10) to enterprise-ready by addressing the 12 requirements identified in the Gemini 3.1 code review and PRD.

**Architecture:** No architectural rewrites. We extend the existing architecture (scored 9.5/10) by adding CI/CD, improving test coverage, extracting interfaces for extensibility, and adding observability exports. All changes are additive or surgical refactors.

**Tech Stack:** Go 1.25+, GitHub Actions, `prometheus/client_golang`, Mermaid diagrams, native Go fuzzing.

**Source Documents:**
- `Gemini 3.1 - Révision de code.md` — Code review (8.6/10)
- `Gemini 3.1 - prd.md` — PRD with 12 requirements across 3 phases

**Open Questions Resolved:**
- **Q1** (bump allocator location): Keep as `internal/` — no separate Go module.
- **Q2** (C4 format): Mermaid — already exists in `docs/architecture/`, just embed in README.
- **Q3** (Prometheus endpoint): HTTP `/metrics` endpoint via `promhttp` — standard, simplest.
- **Q4** (Fuzz in CI): Nightly build — too slow for every PR (~30s per fuzz target × 10k iterations).

---

## Phase 1 — Fondations (R1, R2, R3)

*No dependencies. All three requirements are parallelizable.*

---

### Task 1: GitHub Actions CI Workflow (prerequisite for R1)

**Context:** No CI/CD exists. We need a foundation before adding fuzz pipelines.

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create the CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        go-version: ['1.25']
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ matrix.go-version }}

      - name: Install dependencies
        run: go mod download

      - name: Vet
        run: go vet ./...

      - name: Test with coverage
        run: go test -v -race -cover -coverprofile=coverage.out ./...

      - name: Check coverage threshold
        run: |
          TOTAL=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
          echo "Total coverage: ${TOTAL}%"
          if (( $(echo "$TOTAL < 75" | bc -l) )); then
            echo "Coverage ${TOTAL}% is below 75% threshold"
            exit 1
          fi

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.25'

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v6
        with:
          version: latest
```

**Step 2: Validate locally**

Run: `act -j test` (if `act` is installed) or review the YAML manually for syntax.

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI workflow with test and lint jobs"
```

---

### Task 2: Fuzz Testing CI Pipeline (R1)

**Context:** 5 fuzz tests already exist in `internal/fibonacci/fibonacci_fuzz_test.go`. The PRD requires a CI pipeline running them with 10,000 iterations. Fuzz testing is slow — run as nightly, not per-PR.

**Files:**
- Create: `.github/workflows/fuzz.yml`

**Step 1: Create the nightly fuzz workflow**

```yaml
name: Fuzz Testing

on:
  schedule:
    - cron: '0 3 * * *'  # Nightly at 3:00 UTC
  workflow_dispatch: {}    # Manual trigger

permissions:
  contents: read

jobs:
  fuzz:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        fuzz-target:
          - FuzzFastDoublingConsistency
          - FuzzFFTBasedConsistency
          - FuzzFibonacciIdentities
          - FuzzFastDoublingMod
          - FuzzProgressMonotonicity
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.25'

      - name: Run fuzz test (${{ matrix.fuzz-target }})
        run: |
          go test -fuzz=${{ matrix.fuzz-target }} \
            -fuzztime=10000x \
            ./internal/fibonacci/
        timeout-minutes: 30

      - name: Upload crash artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: fuzz-crash-${{ matrix.fuzz-target }}
          path: internal/fibonacci/testdata/fuzz/
```

**Step 2: Verify fuzz tests pass locally (abbreviated run)**

Run: `go test -fuzz=FuzzFastDoublingConsistency -fuzztime=100x ./internal/fibonacci/`
Expected: PASS (100 iterations, no panics)

Run: `go test -fuzz=FuzzFFTBasedConsistency -fuzztime=100x ./internal/fibonacci/`
Expected: PASS

**Step 3: Commit**

```bash
git add .github/workflows/fuzz.yml
git commit -m "ci: add nightly fuzz testing pipeline for 5 fuzz targets (R1)"
```

**Acceptance criteria (R1):**
- [x] Pipeline CI with `go test -fuzz` covering 5 targets
- [x] 10,000 iterations per target (`-fuzztime=10000x`)
- [x] Crash artifacts uploaded on failure
- [x] Nightly schedule + manual trigger

---

### Task 3: GitHub Templates (R2)

**Context:** No `.github/` directory exists. Create issue templates and PR template.

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/pull_request_template.md`

**Step 1: Create bug report template**

```markdown
---
name: Bug Report
about: Report a bug in FibGo
title: '[BUG] '
labels: bug
assignees: ''
---

## Description

A clear description of the bug.

## Steps to Reproduce

1. Run `fibcalc ...`
2. Observe ...

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened. Include error messages or incorrect output.

## Environment

- **OS:** (e.g., Ubuntu 24.04, Windows 11, macOS 15)
- **Go version:** (output of `go version`)
- **FibGo version:** (output of `fibcalc --version`)
- **Architecture:** (e.g., amd64, arm64)

## Additional Context

Relevant logs, screenshots, or profiling data.
```

**Step 2: Create feature request template**

```markdown
---
name: Feature Request
about: Suggest an enhancement for FibGo
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Problem Statement

What problem does this solve? Why is it needed?

## Proposed Solution

Describe the feature or change you'd like.

## Alternatives Considered

What other approaches did you consider?

## Additional Context

Any benchmarks, references, or related issues.
```

**Step 3: Create PR template**

```markdown
## Summary

Brief description of changes.

## Related Issue

Closes #

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring (no functional change)
- [ ] Documentation
- [ ] Performance improvement
- [ ] Test improvement

## Testing

- [ ] All existing tests pass (`go test -race ./...`)
- [ ] New tests added for changes
- [ ] Fuzz tests pass (if applicable)

## Checklist

- [ ] Code follows project conventions
- [ ] Self-reviewed the diff
- [ ] Comments added where logic isn't self-evident
- [ ] Documentation updated (if applicable)
```

**Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/bug_report.md .github/ISSUE_TEMPLATE/feature_request.md .github/pull_request_template.md
git commit -m "chore: add GitHub issue and PR templates (R2)"
```

**Acceptance criteria (R2):**
- [x] `.github/ISSUE_TEMPLATE/bug_report.md` created
- [x] `.github/ISSUE_TEMPLATE/feature_request.md` created
- [x] `.github/pull_request_template.md` created

---

### Task 4: Measure Current Per-Package Coverage (R3 — diagnostic)

**Context:** Global coverage is ~80%. PRD requires ≥90% on `internal/fibonacci/` and `internal/bigfft/`. First, measure precisely.

**Files:**
- None (diagnostic step)

**Step 1: Run per-package coverage**

Run:
```bash
go test -cover ./internal/fibonacci/ ./internal/bigfft/
```
Expected: Output showing coverage percentage per package. Record the numbers.

**Step 2: Generate detailed coverage report**

Run:
```bash
go test -coverprofile=coverage.out ./internal/fibonacci/ ./internal/bigfft/
go tool cover -func=coverage.out | sort -t: -k3 -n
```
Expected: Function-by-function coverage. Identify uncovered functions.

**Step 3: Document gaps**

Create a working list of uncovered functions/branches to guide Task 5.

---

### Task 5: Increase Coverage to ≥90% on `internal/fibonacci/` (R3)

**Context:** Based on Task 4 diagnostics, write tests for uncovered paths. Use table-driven tests, match existing style.

**Files:**
- Modify: Test files in `internal/fibonacci/` (exact files depend on Task 4 results)

**Approach:** For each uncovered function identified in Task 4:

**Step 1: Write a failing test for the uncovered path**

```go
func TestUncoveredFunction_EdgeCase(t *testing.T) {
    tests := []struct {
        name     string
        input    uint64
        expected string
    }{
        // Cases targeting uncovered branches
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Exercise the uncovered path
        })
    }
}
```

**Step 2: Run test to verify it exercises the uncovered code**

Run: `go test -v -run TestUncoveredFunction -cover ./internal/fibonacci/`
Expected: Test passes AND coverage increases.

**Step 3: Repeat until ≥90%**

Run: `go test -cover ./internal/fibonacci/`
Expected: `coverage: ≥90.0% of statements`

**Step 4: Commit**

```bash
git add internal/fibonacci/*_test.go
git commit -m "test(fibonacci): increase coverage to ≥90% (R3)"
```

---

### Task 6: Increase Coverage to ≥90% on `internal/bigfft/` (R3)

**Context:** Same approach as Task 5, for the bigfft package.

**Files:**
- Modify: Test files in `internal/bigfft/`

**Step 1–3:** Same TDD loop as Task 5, targeting `internal/bigfft/`.

Run: `go test -cover ./internal/bigfft/`
Expected: `coverage: ≥90.0% of statements`

**Step 4: Commit**

```bash
git add internal/bigfft/*_test.go
git commit -m "test(bigfft): increase coverage to ≥90% (R3)"
```

---

### Task 7: Update Coverage Threshold in CI (R3 — finalization)

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add per-package coverage checks to CI**

Add to the `test` job in `ci.yml`, after the existing coverage step:

```yaml
      - name: Check critical package coverage
        run: |
          go test -coverprofile=fib-cov.out ./internal/fibonacci/
          FIB=$(go tool cover -func=fib-cov.out | grep total | awk '{print $3}' | sed 's/%//')
          echo "fibonacci coverage: ${FIB}%"

          go test -coverprofile=fft-cov.out ./internal/bigfft/
          FFT=$(go tool cover -func=fft-cov.out | grep total | awk '{print $3}' | sed 's/%//')
          echo "bigfft coverage: ${FFT}%"

          FAIL=0
          if (( $(echo "$FIB < 90" | bc -l) )); then
            echo "FAIL: fibonacci coverage ${FIB}% < 90%"
            FAIL=1
          fi
          if (( $(echo "$FFT < 90" | bc -l) )); then
            echo "FAIL: bigfft coverage ${FFT}% < 90%"
            FAIL=1
          fi
          exit $FAIL
```

**Step 2: Update CONTRIBUTING.md coverage target**

Change the target from 75% to 90% for critical packages.

In `CONTRIBUTING.md`, find the line mentioning `>75% code coverage` and update:
```
> Critical packages (`internal/fibonacci/`, `internal/bigfft/`): ≥90% code coverage.
> All other packages: ≥75% code coverage.
```

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml CONTRIBUTING.md
git commit -m "ci: enforce ≥90% coverage on critical packages (R3)"
```

**Acceptance criteria (R3):**
- [x] `go test -cover ./internal/fibonacci/` shows ≥90%
- [x] `go test -cover ./internal/bigfft/` shows ≥90%
- [x] CI enforces the threshold
- [x] CONTRIBUTING.md updated

---

## Phase 2 — Extensibilité & Observabilité (R4, R5, R6, R7)

*Dependencies: R5 benefits from R4 (refactoring context). R7 depends on Q3 resolution (HTTP endpoint — resolved above).*

---

### Task 8: Extract Algorithm Strategy Interfaces to Shared Package (R4)

**Context:** `Multiplier` and `DoublingStepExecutor` interfaces are in `internal/fibonacci/strategy.go`. The `Calculator` interface is in `internal/fibonacci/calculator.go`. Extract public-facing interfaces to `internal/strategy/` so third-party algorithm implementations don't need to import fibonacci internals.

**Files:**
- Create: `internal/strategy/strategy.go`
- Create: `internal/strategy/strategy_test.go`
- Modify: `internal/fibonacci/strategy.go` — add type aliases for backward compatibility
- Modify: `internal/fibonacci/calculator.go` — add type alias for Calculator interface

**Step 1: Write a test that imports from the new package**

Create `internal/strategy/strategy_test.go`:

```go
package strategy_test

import (
	"math/big"
	"testing"

	"github.com/agbru/fibcalc/internal/strategy"
)

// Verify interfaces are implementable from outside fibonacci package.
type mockMultiplier struct{}

func (m *mockMultiplier) Multiply(a, b *big.Int) *big.Int {
	return new(big.Int).Mul(a, b)
}

func (m *mockMultiplier) Square(a *big.Int) *big.Int {
	return new(big.Int).Mul(a, a)
}

func (m *mockMultiplier) Name() string { return "mock" }

func TestMultiplierInterface(t *testing.T) {
	var m strategy.Multiplier = &mockMultiplier{}
	result := m.Multiply(big.NewInt(3), big.NewInt(4))
	if result.Int64() != 12 {
		t.Errorf("expected 12, got %d", result.Int64())
	}
}
```

**Step 2: Run test — expect compilation failure**

Run: `go test -v -run TestMultiplierInterface ./internal/strategy/`
Expected: FAIL — package doesn't exist yet.

**Step 3: Create `internal/strategy/strategy.go`**

```go
// Package strategy defines interfaces for Fibonacci algorithm strategies.
// These interfaces allow third-party implementations without importing
// the internal fibonacci package directly.
package strategy

import "math/big"

// Multiplier is a narrow interface for multiply/square operations.
type Multiplier interface {
	Multiply(a, b *big.Int) *big.Int
	Square(a *big.Int) *big.Int
	Name() string
}
```

Note: Only extract `Multiplier` initially. `DoublingStepExecutor` depends on internal types (`DoublingState`) and is not suitable for third-party use without additional work. `Calculator` is already public in fibonacci. Keep scope minimal.

**Step 4: Run test — expect pass**

Run: `go test -v -run TestMultiplierInterface ./internal/strategy/`
Expected: PASS

**Step 5: Add type alias in `internal/fibonacci/strategy.go` for backward compatibility**

At the top of `internal/fibonacci/strategy.go`, add:

```go
import "github.com/agbru/fibcalc/internal/strategy"

// Multiplier is an alias for strategy.Multiplier for backward compatibility.
type Multiplier = strategy.Multiplier
```

**Step 6: Run all tests to verify no regressions**

Run: `go test -race ./...`
Expected: All tests pass.

**Step 7: Commit**

```bash
git add internal/strategy/ internal/fibonacci/strategy.go
git commit -m "refactor: extract Multiplier interface to internal/strategy (R4)"
```

**Acceptance criteria (R4):**
- [x] `Multiplier` interface defined in `internal/strategy/`
- [x] Existing strategies still compile (type alias)
- [x] Mock implementation compiles from outside fibonacci package
- [x] All tests pass

---

### Task 9: Cyclomatic Complexity Audit on `internal/bigfft/` (R5)

**Context:** `.golangci.yml` limits cyclomatic complexity to 15. Audit `internal/bigfft/` for functions exceeding this. Refactor or document with justification.

**Files:**
- Possibly modify: Files in `internal/bigfft/` with high-complexity functions
- Create: `docs/architecture/complexity-audit.md` (if justifications needed)

**Step 1: Run complexity analysis**

Run:
```bash
golangci-lint run --enable gocyclo --no-config ./internal/bigfft/
```
Expected: List of functions exceeding complexity threshold (if any).

Alternative if `golangci-lint` is not available:
```bash
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
gocyclo -over 15 ./internal/bigfft/
```

**Step 2: For each function exceeding CC=15**

Decision tree:
- **Can it be refactored?** Extract helper functions, simplify branches. Refactor and test.
- **Is the complexity inherent to the algorithm?** Document with a `//nolint:gocyclo` comment and add justification to `docs/architecture/complexity-audit.md`.

**Step 3: Run lint to verify compliance**

Run: `golangci-lint run ./internal/bigfft/`
Expected: No complexity warnings (all resolved or documented).

**Step 4: Run all tests**

Run: `go test -race ./internal/bigfft/`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add internal/bigfft/ docs/architecture/complexity-audit.md
git commit -m "refactor(bigfft): address cyclomatic complexity findings (R5)"
```

**Acceptance criteria (R5):**
- [x] `gocyclo` report generated
- [x] Functions >15 refactored or documented with justification
- [x] All tests pass after refactoring

---

### Task 10: Embed C4 Diagram in README (R6)

**Context:** C4 Mermaid diagrams already exist at `docs/architecture/system-context.mermaid` and `docs/architecture/container-diagram.mermaid`. Embed the Context + Container diagrams in `README.md`.

**Files:**
- Modify: `README.md`
- Reference: `docs/architecture/system-context.mermaid`, `docs/architecture/container-diagram.mermaid`

**Step 1: Read the existing mermaid files**

Read `docs/architecture/system-context.mermaid` and `docs/architecture/container-diagram.mermaid`.

**Step 2: Add C4 section to README**

In `README.md`, find the `## Architecture` section. Add after the existing architecture content:

````markdown
### System Architecture (C4 Model)

#### Context Diagram

```mermaid
<contents of system-context.mermaid>
```

#### Container Diagram

```mermaid
<contents of container-diagram.mermaid>
```

> Full architecture documentation: [docs/architecture/README.md](docs/architecture/README.md)
````

**Step 3: Verify rendering**

Open the README in GitHub or a Mermaid-capable viewer to confirm diagrams render correctly.

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: embed C4 context and container diagrams in README (R6)"
```

**Acceptance criteria (R6):**
- [x] Mermaid C4 diagrams visible in README
- [x] Context (Level 1) and Container (Level 2) both present
- [x] Links to full architecture docs

---

### Task 11: Prometheus Metrics Export (R7)

**Context:** `internal/metrics/` collects performance and memory metrics for display only. Add Prometheus export via `prometheus/client_golang`. Expose an HTTP `/metrics` endpoint when `--metrics-addr` flag is set.

**Files:**
- Create: `internal/metrics/prometheus.go`
- Create: `internal/metrics/prometheus_test.go`
- Modify: `internal/config/config.go` — add `--metrics-addr` flag
- Modify: `internal/app/app.go` — start metrics server if flag set
- Modify: `go.mod` — add `prometheus/client_golang`

**Step 1: Add dependency**

Run: `go get github.com/prometheus/client_golang/prometheus`
Run: `go get github.com/prometheus/client_golang/prometheus/promhttp`

**Step 2: Write a failing test for the Prometheus exporter**

Create `internal/metrics/prometheus_test.go`:

```go
package metrics_test

import (
	"strings"
	"testing"

	"github.com/agbru/fibcalc/internal/metrics"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/testutil"
)

func TestPrometheusExporter_UpdateFromIndicators(t *testing.T) {
	reg := prometheus.NewRegistry()
	exp := metrics.NewPrometheusExporter(reg)

	indicators := &metrics.Indicators{
		BitsPerSecond:   1000.0,
		DigitsPerSecond: 300.0,
		DoublingSteps:   20,
		StepsPerSecond:  500.0,
	}
	exp.Update(indicators)

	count := testutil.CollectAndCount(exp, "fibcalc_bits_per_second")
	if count == 0 {
		t.Error("expected fibcalc_bits_per_second metric to be registered")
	}

	val := testutil.ToFloat64(exp.BitsPerSecond)
	if val != 1000.0 {
		t.Errorf("expected 1000.0, got %f", val)
	}
}
```

**Step 3: Run test — expect failure**

Run: `go test -v -run TestPrometheusExporter ./internal/metrics/`
Expected: FAIL — `NewPrometheusExporter` doesn't exist.

**Step 4: Implement the Prometheus exporter**

Create `internal/metrics/prometheus.go`:

```go
package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
)

// PrometheusExporter exposes FibGo metrics as Prometheus gauges.
type PrometheusExporter struct {
	BitsPerSecond   prometheus.Gauge
	DigitsPerSecond prometheus.Gauge
	DoublingSteps   prometheus.Gauge
	StepsPerSecond  prometheus.Gauge
	HeapAlloc       prometheus.Gauge
	NumGC           prometheus.Gauge
}

// NewPrometheusExporter creates and registers Prometheus metrics.
func NewPrometheusExporter(reg prometheus.Registerer) *PrometheusExporter {
	e := &PrometheusExporter{
		BitsPerSecond: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_bits_per_second",
			Help: "Bits of result computed per second.",
		}),
		DigitsPerSecond: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_digits_per_second",
			Help: "Estimated decimal digits computed per second.",
		}),
		DoublingSteps: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_doubling_steps_total",
			Help: "Number of doubling iterations.",
		}),
		StepsPerSecond: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_steps_per_second",
			Help: "Doubling steps executed per second.",
		}),
		HeapAlloc: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_heap_alloc_bytes",
			Help: "Current heap allocation in bytes.",
		}),
		NumGC: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "fibcalc_gc_cycles_total",
			Help: "Number of completed GC cycles.",
		}),
	}
	reg.MustRegister(e.BitsPerSecond, e.DigitsPerSecond, e.DoublingSteps,
		e.StepsPerSecond, e.HeapAlloc, e.NumGC)
	return e
}

// Update sets gauge values from computed Indicators.
func (e *PrometheusExporter) Update(ind *Indicators) {
	e.BitsPerSecond.Set(ind.BitsPerSecond)
	e.DigitsPerSecond.Set(ind.DigitsPerSecond)
	e.DoublingSteps.Set(float64(ind.DoublingSteps))
	e.StepsPerSecond.Set(ind.StepsPerSecond)
}

// UpdateMemory sets gauge values from a MemorySnapshot.
func (e *PrometheusExporter) UpdateMemory(snap *MemorySnapshot) {
	e.HeapAlloc.Set(float64(snap.HeapAlloc))
	e.NumGC.Set(float64(snap.NumGC))
}

// Describe implements prometheus.Collector.
func (e *PrometheusExporter) Describe(ch chan<- *prometheus.Desc) {
	e.BitsPerSecond.Describe(ch)
	e.DigitsPerSecond.Describe(ch)
	e.DoublingSteps.Describe(ch)
	e.StepsPerSecond.Describe(ch)
	e.HeapAlloc.Describe(ch)
	e.NumGC.Describe(ch)
}

// Collect implements prometheus.Collector.
func (e *PrometheusExporter) Collect(ch chan<- prometheus.Metric) {
	e.BitsPerSecond.Collect(ch)
	e.DigitsPerSecond.Collect(ch)
	e.DoublingSteps.Collect(ch)
	e.StepsPerSecond.Collect(ch)
	e.HeapAlloc.Collect(ch)
	e.NumGC.Collect(ch)
}
```

**Step 5: Run test — expect pass**

Run: `go test -v -run TestPrometheusExporter ./internal/metrics/`
Expected: PASS

**Step 6: Add `--metrics-addr` flag to config**

In `internal/config/config.go`, add to the `AppConfig` struct:

```go
MetricsAddr string // Address for Prometheus metrics endpoint (e.g., ":2112")
```

Add flag parsing:

```go
flag.StringVar(&cfg.MetricsAddr, "metrics-addr", "", "Address to expose Prometheus metrics (e.g., :2112)")
```

**Step 7: Start metrics server in app.go**

In `internal/app/app.go`, in the `Run()` function, before calculation dispatch:

```go
if a.config.MetricsAddr != "" {
	reg := prometheus.NewRegistry()
	a.promExporter = metrics.NewPrometheusExporter(reg)
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{}))
	go http.ListenAndServe(a.config.MetricsAddr, mux)
}
```

Update the exporter after each calculation completes with `a.promExporter.Update(indicators)`.

**Step 8: Run all tests**

Run: `go test -race ./...`
Expected: All tests pass.

**Step 9: Commit**

```bash
git add internal/metrics/prometheus.go internal/metrics/prometheus_test.go \
       internal/config/config.go internal/app/app.go go.mod go.sum
git commit -m "feat(metrics): add Prometheus metrics export via --metrics-addr (R7)"
```

**Acceptance criteria (R7):**
- [x] `--metrics-addr :2112` starts HTTP server with `/metrics` endpoint
- [x] 6 Prometheus gauges exported (bits/s, digits/s, steps, steps/s, heap, GC)
- [x] Metrics update after calculation
- [x] Tests pass

---

## Phase 3 — Polish & Communauté (R8, R9, R10, R11, R12)

*Dependencies: R8 depends on R4 (interfaces extracted). R10 depends on R4 (API stabilized).*

---

### Task 12: Isolate Bump Allocator (R8)

**Context:** `BumpAllocator` in `internal/bigfft/bump.go` is already decoupled via `TempAllocator` interface. Extract the generic bump-allocation logic (not the fermat-specific parts) to `internal/allocator/`.

**Files:**
- Create: `internal/allocator/bump.go` — generic bump allocator for `big.Word` slices
- Create: `internal/allocator/bump_test.go`
- Modify: `internal/bigfft/bump.go` — delegate to `internal/allocator/`

**Step 1: Write a failing test for the generic allocator**

Create `internal/allocator/bump_test.go`:

```go
package allocator_test

import (
	"math/big"
	"testing"

	"github.com/agbru/fibcalc/internal/allocator"
)

func TestBumpAllocator_Alloc(t *testing.T) {
	alloc := allocator.NewBump(1024)
	slice := alloc.AllocWords(128)
	if len(slice) != 128 {
		t.Errorf("expected len 128, got %d", len(slice))
	}
}

func TestBumpAllocator_Reset(t *testing.T) {
	alloc := allocator.NewBump(1024)
	alloc.AllocWords(512)
	alloc.Reset()
	slice := alloc.AllocWords(1024)
	if len(slice) != 1024 {
		t.Errorf("expected len 1024 after reset, got %d", len(slice))
	}
}
```

**Step 2: Run test — expect failure**

Run: `go test -v ./internal/allocator/`
Expected: FAIL — package doesn't exist.

**Step 3: Implement generic bump allocator**

Create `internal/allocator/bump.go`:

```go
// Package allocator provides a generic O(1) bump allocator for big.Word slices.
package allocator

import "math/big"

// Bump is a bump-pointer allocator for big.Word slices.
// It pre-allocates a contiguous block and serves sub-slices via pointer bumping.
// Call Reset() to reclaim all allocations at once.
type Bump struct {
	buf    []big.Word
	offset int
}

// NewBump creates a bump allocator with capacity for n words.
func NewBump(n int) *Bump {
	return &Bump{buf: make([]big.Word, n)}
}

// AllocWords returns a zeroed slice of n words from the arena.
// Returns nil if insufficient space remains.
func (b *Bump) AllocWords(n int) []big.Word {
	if b.offset+n > len(b.buf) {
		return nil
	}
	s := b.buf[b.offset : b.offset+n : b.offset+n]
	for i := range s {
		s[i] = 0
	}
	b.offset += n
	return s
}

// Reset reclaims all allocations. Does not zero memory.
func (b *Bump) Reset() {
	b.offset = 0
}

// Remaining returns the number of words still available.
func (b *Bump) Remaining() int {
	return len(b.buf) - b.offset
}
```

**Step 4: Run test — expect pass**

Run: `go test -v ./internal/allocator/`
Expected: PASS

**Step 5: Update `internal/bigfft/bump.go` to delegate**

Modify `internal/bigfft/bump.go` to use `internal/allocator.Bump` internally where the generic word-allocation logic overlaps, keeping fermat-specific wrapping in bigfft.

**Step 6: Run all tests**

Run: `go test -race ./...`
Expected: All tests pass.

**Step 7: Commit**

```bash
git add internal/allocator/ internal/bigfft/bump.go
git commit -m "refactor: extract generic bump allocator to internal/allocator (R8)"
```

---

### Task 13: Document Unsafe Usage (R9)

**Context:** Only 2 files use `unsafe`:
1. `internal/bigfft/fft.go:13` — `unsafe.Sizeof(big.Word(0))` for word-size constant
2. `internal/bigfft/arith_decl.go:23` — blank import for `go:linkname`
3. `internal/fibonacci/memory/arena_test.go:53-56` — test-only pointer arithmetic

**Files:**
- Create: `docs/architecture/unsafe-audit.md`

**Step 1: Create the audit document**

```markdown
# Unsafe Usage Audit

**Date:** 2026-02-20
**Scope:** All uses of `unsafe` and `go:linkname` in FibGo.

## Summary

FibGo uses `unsafe` in 3 locations, all justified and isolated.

## Inventory

### 1. `internal/bigfft/fft.go:13`

```go
const _W = int(unsafe.Sizeof(big.Word(0)) * 8)
```

**Purpose:** Determine platform word size (32 or 64 bits) at compile time.
**Risk:** None. `unsafe.Sizeof` is a compile-time constant with no runtime risk.
**Invariant:** `_W` is always 32 or 64.

### 2. `internal/bigfft/arith_decl.go`

```go
import _ "unsafe" // Required for go:linkname
```

**Purpose:** Access 7 internal `math/big` assembly functions via `go:linkname`:
`addVV`, `subVV`, `addVW`, `subVW`, `shlVU`, `mulAddVWW`, `addMulVVW`.

**Risk:** Medium. `go:linkname` bypasses Go's export rules. Functions may change signature between Go versions.
**Mitigation:**
- Guarded by build tags (`arith_amd64.go` vs `arith_generic.go`)
- Generic fallback exists for all 7 functions
- CI tests on each Go version detect breakage immediately

### 3. `internal/fibonacci/memory/arena_test.go:53-56`

```go
pi := uintptr(unsafe.Pointer(&bi[:cap(bi)][0]))
```

**Purpose:** Test-only. Verifies arena allocations don't overlap in memory.
**Risk:** None. Test code only, never runs in production.
**Invariant:** Arena-allocated slices have non-overlapping backing arrays.
```

**Step 2: Commit**

```bash
git add docs/architecture/unsafe-audit.md
git commit -m "docs: add unsafe usage audit with justifications (R9)"
```

---

### Task 14: Library Usage Examples in README (R10)

**Context:** 4 example tests exist in `internal/fibonacci/example_test.go` but no README section. Add a "Library Usage" section to README with runnable examples.

**Files:**
- Modify: `README.md`

**Step 1: Add Library Usage section**

In `README.md`, after the "Usage Guide" section (or before "Performance Benchmarks"), add:

````markdown
## Library Usage

FibGo can be imported as a Go library. Add the dependency:

```bash
go get github.com/agbru/fibcalc
```

### Basic Calculation

```go
package main

import (
	"context"
	"fmt"

	"github.com/agbru/fibcalc/internal/fibonacci"
)

func main() {
	factory := fibonacci.NewDefaultFactory()
	calc, _ := factory.Get("fast")

	result, err := calc.Calculate(context.Background(), 1000, nil)
	if err != nil {
		panic(err)
	}
	fmt.Printf("F(1000) = %s\n", result.String())
}
```

### Using the Factory to Compare Algorithms

```go
factory := fibonacci.NewDefaultFactory()
for _, name := range factory.List() {
	calc, _ := factory.Get(name)
	result, _ := calc.Calculate(context.Background(), 100, nil)
	fmt.Printf("%s: F(100) = %s\n", calc.Name(), result.String())
}
```

> See [example tests](internal/fibonacci/example_test.go) for progress tracking and observer patterns.
````

**Step 2: Verify examples compile**

Run: `go vet ./...`
Expected: No errors.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add library usage examples to README (R10)"
```

---

### Task 15: Structured JSON Log Flag (R11)

**Context:** Zerolog already outputs structured JSON by default. The current setup uses `zerolog.ConsoleWriter` for human-readable output. Add a `--log-format` flag to choose between `text` (default) and `json`.

**Files:**
- Modify: `internal/config/config.go` — add `--log-format` flag
- Modify: `internal/app/app.go` — configure zerolog output based on flag
- Create: `internal/app/logging_test.go`

**Step 1: Write a failing test**

Create `internal/app/logging_test.go`:

```go
package app_test

import (
	"testing"
)

func TestLogFormatFlag_JSON(t *testing.T) {
	// Verify that --log-format=json produces parseable JSON output
	// (integration test via CLI)
}
```

**Step 2: Add `--log-format` flag**

In `internal/config/config.go`, add to `AppConfig`:

```go
LogFormat string // "text" (default) or "json"
```

Add flag:

```go
flag.StringVar(&cfg.LogFormat, "log-format", "text", "Log output format: text or json")
```

**Step 3: Configure zerolog based on flag**

In `internal/app/app.go`, in the initialization:

```go
if a.config.LogFormat == "json" {
	// zerolog defaults to JSON — no ConsoleWriter needed
	log.Logger = zerolog.New(os.Stderr).With().Timestamp().Logger()
} else {
	// Human-readable console output (existing behavior)
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
}
```

**Step 4: Run all tests**

Run: `go test -race ./...`
Expected: All tests pass.

**Step 5: Verify manually**

Run: `go run ./cmd/fibcalc --log-level=debug --log-format=json 100`
Expected: JSON log lines on stderr, parseable by `jq`.

**Step 6: Commit**

```bash
git add internal/config/config.go internal/app/app.go internal/app/logging_test.go
git commit -m "feat(app): add --log-format flag for JSON structured logging (R11)"
```

---

### Task 16: Code of Conduct (R12)

**Context:** CONTRIBUTING.md has an inline conduct section. Create a proper standalone `CODE_OF_CONDUCT.md` using the Contributor Covenant v2.1.

**Files:**
- Create: `CODE_OF_CONDUCT.md`
- Modify: `CONTRIBUTING.md` — reference the standalone file

**Step 1: Create `CODE_OF_CONDUCT.md`**

Use the standard Contributor Covenant v2.1 text from https://www.contributor-covenant.org/version/2/1/code_of_conduct/ with contact email set to the repository owner.

**Step 2: Update CONTRIBUTING.md**

Replace the inline Code of Conduct section with:

```markdown
## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.
```

**Step 3: Commit**

```bash
git add CODE_OF_CONDUCT.md CONTRIBUTING.md
git commit -m "chore: add Contributor Covenant Code of Conduct (R12)"
```

---

## Execution Summary

| Task | Requirement | Phase | Est. Complexity |
|------|-------------|-------|----------------|
| 1  | (prereq)  | 1 | Low — YAML file |
| 2  | R1        | 1 | Low — YAML file |
| 3  | R2        | 1 | Low — 3 markdown files |
| 4  | R3 (diag) | 1 | Low — diagnostic |
| 5  | R3        | 1 | High — write tests until ≥90% |
| 6  | R3        | 1 | High — write tests until ≥90% |
| 7  | R3 (CI)   | 1 | Low — CI update |
| 8  | R4        | 2 | Medium — interface extraction |
| 9  | R5        | 2 | Medium — audit + refactor |
| 10 | R6        | 2 | Low — embed existing diagrams |
| 11 | R7        | 2 | Medium — new package + flag |
| 12 | R8        | 3 | Medium — extract allocator |
| 13 | R9        | 3 | Low — documentation |
| 14 | R10       | 3 | Low — README section |
| 15 | R11       | 3 | Low — flag + zerolog config |
| 16 | R12       | 3 | Low — markdown file |

**Parallelizable tasks within each phase:**
- Phase 1: Tasks 1-3 in parallel, then 4→5→6→7 sequentially
- Phase 2: Tasks 9, 10 in parallel; Task 8 then 11
- Phase 3: Tasks 12-16 largely parallelizable (12 depends on 8)
