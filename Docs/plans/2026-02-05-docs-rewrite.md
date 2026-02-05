# Docs/ Full Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite all 8 documentation files in `Docs/` from scratch in English, grounded in the actual codebase, with no stale references.

**Architecture:** Same 8-file structure. Each doc is verified against actual source code. No `./fibcalc` CLI examples (entry point removed). All examples use `go test -bench` or Go API. All in English.

**Tech Stack:** Markdown documentation only. No code changes.

---

## Cross-Cutting Rules (apply to ALL tasks)

1. **No `./fibcalc` CLI examples anywhere.** The `cmd/fibcalc` entry point was removed. Show `go test -bench` commands and Go API usage instead. Where CLI flags are relevant, document them as "configuration options" with a note that the entry point needs to be rebuilt.
2. **No version/date headers.** Remove all "Version: X.Y.Z / Last Updated" — git history tracks this.
3. **Go 1.25.0** everywhere (from `go.mod`).
4. **Module name:** `github.com/agbru/fibcalc`
5. **All English.** Translate `PROGRESS_BAR_ALGORITHM.md` from French.
6. **Accurate interface/type/function names** — taken from actual source code in this plan.
7. **No emoji ratings** (remove star ratings from COMPARISON.md).
8. **Mermaid diagrams** are kept where they exist (they render on GitHub).

## Reference: Actual Source Code Facts

### Interfaces
- `Calculator`: `Calculate(ctx, progressChan, calcIndex, n, opts) (*big.Int, error)` + `Name() string`
- `coreCalculator`: `CalculateCore(ctx, reporter, n, opts) (*big.Int, error)` + `Name() string`
- `CalculatorFactory`: `Create`, `Get`, `List`, `Register`, `GetAll`
- `MultiplicationStrategy`: `Multiply`, `Square`, `Name`, `ExecuteStep`
- `ProgressObserver`: `Update(calcIndex int, progress float64)`
- orchestration `ProgressReporter`: `DisplayProgress(wg, progressChan, numCalculators, out)`
- orchestration `ResultPresenter`: `PresentComparisonTable`, `PresentResult`, `FormatDuration`, `HandleError`

### Registered Algorithms
- `"fast"` → `OptimizedFastDoubling{}`
- `"matrix"` → `MatrixExponentiation{}`
- `"fft"` → `FFTBasedCalculator{}`
- `"gmp"` → auto-registered via `init()` when built with `-tags=gmp`

### Strategy Implementations
- `AdaptiveStrategy` — "Adaptive (Karatsuba/FFT)"
- `FFTOnlyStrategy` — "FFT-Only"
- `KaratsubaStrategy` — "Karatsuba-Only"

### Observer Implementations
- `ChannelObserver` — bridges to `chan<- ProgressUpdate`
- `LoggingObserver` — zerolog with throttling
- `NoOpObserver` — null object

### Constants (from `constants.go`)
- `DefaultParallelThreshold = 4096` bits
- `DefaultFFTThreshold = 500_000` bits
- `DefaultStrassenThreshold = 3072` bits
- `ParallelFFTThreshold = 10_000_000` bits
- `DefaultKaratsubaThreshold = 2048` bits
- `ProgressReportThreshold = 0.01` (1%)

### Error Types (from `errors.go`)
- `ConfigError`, `CalculationError`, `ServerError`, `ValidationError`
- Exit codes: 0 (success), 1 (generic), 2 (timeout), 3 (mismatch), 4 (config), 130 (canceled)

### Smart Multiplication Tiers (from `fft.go`)
1. FFT: both operands > `FFTThreshold` → `bigfft.MulTo`
2. Karatsuba: both operands > `KaratsubaThreshold` → `bigfft.KaratsubaMultiplyTo`
3. Standard: `z.Mul(x, y)` via `math/big`

### bigfft Pool Size Classes
64, 256, 1K, 4K, 16K, 64K, 256K, 1M, 4M, 16M words

---

## Task 1: Rewrite `Docs/ARCHITECTURE.md`

**Files:**
- Modify: `Docs/ARCHITECTURE.md`

**Step 1: Write the new ARCHITECTURE.md**

Replace entire file with content that:

- Removes "Version/Last Updated" header
- Fixes architecture diagram: remove `cmd/fibcalc` box, show the 4 layers (Entry Point as "to be rebuilt", Orchestration, Business, Presentation) accurately
- Fixes `cmd/fibcalc` package description: note it does not currently exist, only `cmd/generate-golden` exists
- Fixes `internal/fibonacci` section: add missing files (`options.go`, `doubling_framework.go`, `matrix_framework.go`, `matrix_ops.go`, `matrix_types.go`, `threshold_types.go`, `progress.go`, `observers.go`, `testing.go`, `fft.go`, `generator.go`, `generator_iterative.go`)
- Fixes `internal/bigfft` section: add missing files (`fft_core.go`, `fft_recursion.go`, `fft_poly.go`, `fft_cache.go`, `karatsuba.go`, `allocator.go`, `bump.go`, `memory_est.go`, `scan.go`, `cpu_amd64.go`)
- Adds missing packages: `internal/ui` (colors, themes), `internal/app` (lifecycle, version, app.go)
- Fixes ADRs: keep ADR-001 through ADR-004, verify accuracy
- Fixes Data Flow: remove "routing to CLI mode" (no modes), remove server references
- Fixes "Extensibility" section: register in `registry.go` via `NewDefaultFactory()`, not `main.go`
- Fixes all interface signatures to match actual code

The architecture diagram should be:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ENTRY POINT                                   │
│                                                                         │
│                    ┌────────────────────────┐                           │
│                    │  cmd/fibcalc (removed)  │                          │
│                    │  cmd/generate-golden    │                          │
│                    └───────────┬─────────────┘                          │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                                    │
│                                ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    internal/orchestration                         │   │
│  │  • ExecuteCalculations() — parallel algorithm execution           │   │
│  │  • AnalyzeComparisonResults() — analysis and comparison           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐                  │
│  │    config     │  │  calibration  │  │     app      │                  │
│  │   Parsing     │  │    Tuning     │  │  Lifecycle   │                  │
│  └──────────────┘  └───────────────┘  └──────────────┘                  │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────┐
│                      BUSINESS LAYER                                      │
│                                ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    internal/fibonacci                             │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │   │
│  │  │  Fast Doubling   │  │     Matrix       │  │    FFT-Based   │ │   │
│  │  │  O(log n)        │  │  Exponentiation  │  │    Doubling    │ │   │
│  │  │  Parallel        │  │  O(log n)        │  │    O(log n)    │ │   │
│  │  │  Zero-Alloc      │  │  Strassen        │  │    FFT Mul     │ │   │
│  │  └──────────────────┘  └──────────────────┘  └────────────────┘ │   │
│  │                            │                                     │   │
│  │                            ▼                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐│   │
│  │  │                    internal/bigfft                           ││   │
│  │  │  • FFT/Karatsuba multiplication for very large numbers      ││   │
│  │  │  • Object pooling, bump allocation, SIMD dispatch           ││   │
│  │  └──────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────┐
│                   PRESENTATION LAYER                                     │
│                                ▼                                         │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │         internal/cli             │  │       internal/ui            │ │
│  │  • Spinner and progress bar      │  │  • ANSI color functions     │ │
│  │  • Result formatting             │  │  • Theme system             │ │
│  │  • ETA estimation                │  │  • NO_COLOR support         │ │
│  │  • Shell completion              │  │                              │ │
│  └──────────────────────────────────┘  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

The package table should list ALL packages with accurate file inventories.

The data flow section should be:
```
1. config.ParseConfig() parses CLI flags + env vars → AppConfig
2. app.SetupContext() creates context with timeout + signal handling
3. fibonacci.GlobalFactory() provides calculators by name
4. orchestration.ExecuteCalculations() runs calculators concurrently via errgroup
   - Each Calculator.Calculate() delegates to FibCalculator decorator
   - FibCalculator uses CalculateWithObservers() for progress
   - ProgressSubject notifies ChannelObserver → progressChan
   - ProgressReporter (CLIProgressReporter) displays progress
5. orchestration.AnalyzeComparisonResults() compares results
6. ResultPresenter (CLIResultPresenter) formats and displays output
```

**Step 2: Verify file references**

Run: `dir /s /b "C:\Users\agbru\OneDrive\Documents\GitHub\FibGoIng\internal\fibonacci\*.go" | findstr /v _test`

Confirm all non-test .go files are mentioned in the doc.

**Step 3: Commit**

```bash
git add Docs/ARCHITECTURE.md
git commit -m "docs(architecture): rewrite ARCHITECTURE.md from scratch

Verified against actual codebase. Fixes stale cmd/fibcalc references,
adds missing packages (ui, app) and files, corrects all interface
signatures, updates data flow to reflect observer pattern."
```

---

## Task 2: Rewrite `Docs/PERFORMANCE.md`

**Files:**
- Modify: `Docs/PERFORMANCE.md`

**Step 1: Write the new PERFORMANCE.md**

Replace entire file with content that:

- Removes version/date header
- Updates benchmark config to Go 1.25.0
- Keeps the benchmark table (data is still representative)
- Replaces ALL `./fibcalc` examples with `go test -bench` equivalents:
  ```bash
  # Run all benchmarks
  go test -bench=. -benchmem ./internal/fibonacci/

  # Benchmark specific algorithm
  go test -bench=BenchmarkFastDoubling -benchmem ./internal/fibonacci/

  # CPU profiling
  go test -cpuprofile=cpu.prof -bench=BenchmarkFastDoubling ./internal/fibonacci/
  go tool pprof cpu.prof
  ```
- Fixes the "Tuning Guide" section: remove `./fibcalc --calibrate` examples, describe calibration as API usage or note entry point needs rebuilding
- Fixes the "Configuration Parameters" table: add `--karatsuba-threshold` (missing from old doc, default 2048 bits)
- Fixes the smart multiplication description to show 3 tiers (FFT, Karatsuba, standard) instead of 2
- Updates code snippets to match actual `smartMultiply` signature: `smartMultiply(z, x, y *big.Int, fftThreshold, karatsubaThreshold int)`
- Removes "Recommendations by Workload Type" section (all used `./fibcalc`)
- Keeps "Advanced Optimization Tips" (GOMAXPROCS, CPU affinity, etc.) — these are generic
- Updates build command to note `cmd/fibcalc` doesn't exist

**Step 2: Verify benchmark commands work**

Run: `go test -bench=BenchmarkFastDoubling -benchtime=1x -timeout 30s ./internal/fibonacci/`

Confirm the benchmark command actually runs.

**Step 3: Commit**

```bash
git add Docs/PERFORMANCE.md
git commit -m "docs(performance): rewrite PERFORMANCE.md from scratch

Replaced all dead ./fibcalc examples with go test -bench commands.
Updated to Go 1.25.0. Added 3-tier multiplication explanation.
Added karatsuba-threshold documentation."
```

---

## Task 3: Rewrite `Docs/algorithms/COMPARISON.md`

**Files:**
- Modify: `Docs/algorithms/COMPARISON.md`

**Step 1: Write the new COMPARISON.md**

Replace entire file with content that:

- Removes date header
- Algorithm table: use actual registered names (`fast`, `matrix`, `fft`) and actual `Name()` output
- Keeps theoretical comparison (operation counts per iteration) — this is accurate
- Keeps asymptotic constants analysis — mathematically correct
- Keeps memory comparison — accurate
- Updates benchmark config to Go 1.25.0
- Keeps benchmark data tables (representative)
- Keeps ASCII performance graph
- Replaces "When to Use" CLI examples with Go API:
  ```go
  factory := fibonacci.GlobalFactory()
  calc, _ := factory.Get("fast")
  result, _ := calc.Calculate(ctx, progressChan, 0, 10_000_000, opts)
  ```
- Replaces "Complete Comparison" CLI example with benchmark command:
  ```bash
  go test -bench='Benchmark(FastDoubling|Matrix|FFT)' -benchmem ./internal/fibonacci/
  ```
- Replaces "Configuration Recommendations" CLI examples with Options struct:
  ```go
  opts := fibonacci.Options{
      ParallelThreshold: 4096,
      FFTThreshold:      500_000,
      StrassenThreshold: 3072,
  }
  ```
- Replaces star-rating conclusion table with prose recommendations
- Removes all `./fibcalc` invocations

**Step 2: Commit**

```bash
git add Docs/algorithms/COMPARISON.md
git commit -m "docs(algorithms): rewrite COMPARISON.md from scratch

Replaced CLI examples with Go API and benchmark commands.
Removed star ratings. Kept mathematical analysis intact."
```

---

## Task 4: Rewrite `Docs/algorithms/FAST_DOUBLING.md`

**Files:**
- Modify: `Docs/algorithms/FAST_DOUBLING.md`

**Step 1: Write the new FAST_DOUBLING.md**

Replace entire file with content that:

- Keeps mathematical foundation (matrix form, doubling formulae, formal proof) — all correct
- Keeps mermaid visualization — renders on GitHub
- Keeps pseudocode — correct
- Keeps simplified Go implementation — correct
- Updates "Implemented Optimizations" section:
  - Iterative version: show `DoublingFramework` + `MultiplicationStrategy` pattern instead of raw loop
  - Zero-allocation: keep `sync.Pool` explanation, note `CalculationState` (public type via `AcquireState`/`ReleaseState`)
  - Parallelism: update to show `ExecuteStep` on the strategy, not raw `parallelMultiply3Optimized`
  - Adaptive multiplication: show 3-tier `smartMultiply(z, x, y, fftThreshold, karatsubaThreshold)` signature
- Updates "Usage" section: replace `./fibcalc` with Go API and benchmark commands:
  ```go
  factory := fibonacci.GlobalFactory()
  calc, _ := factory.Get("fast")
  result, _ := calc.Calculate(ctx, progressChan, 0, n, fibonacci.Options{
      ParallelThreshold: 4096,
      FFTThreshold:      500_000,
  })
  ```
  ```bash
  go test -bench=BenchmarkFastDoubling -benchmem ./internal/fibonacci/
  ```
- Keeps references — all valid

**Step 2: Commit**

```bash
git add Docs/algorithms/FAST_DOUBLING.md
git commit -m "docs(algorithms): rewrite FAST_DOUBLING.md from scratch

Updated optimization sections to reflect DoublingFramework/Strategy
pattern. Replaced CLI examples with Go API. Added 3-tier multiply."
```

---

## Task 5: Rewrite `Docs/algorithms/FFT.md`

**Files:**
- Modify: `Docs/algorithms/FFT.md`

**Step 1: Write the new FFT.md**

Replace entire file with content that:

- Keeps mathematical principle (convolution theorem) — correct
- Keeps mermaid sequence diagram — correct
- Updates "Implementation in FibCalc" section:
  - Show actual `bigfft.Mul` signature: `func Mul(x, y *big.Int) (res *big.Int, err error)`
  - Show actual `bigfft.MulTo` signature: `func MulTo(z, x, y *big.Int) (res *big.Int, err error)`
  - Show 3-tier `smartMultiply` with both `fftThreshold` and `karatsubaThreshold` params
  - Update code structure to include ALL files: `fft.go`, `fft_core.go`, `fft_recursion.go`, `fft_poly.go`, `fft_cache.go`, `fermat.go`, `karatsuba.go`, `pool.go`, `allocator.go`, `bump.go`, `memory_est.go`, `scan.go`, `arith_amd64.go`, `arith_amd64.s`, `arith_decl.go`, `cpu_amd64.go`
- Updates "Activation Threshold" section: replace `./fibcalc` examples with Options struct
- Keeps "Interaction with Parallelism" section — accurate (FFT saturates CPU)
- Updates FFTBasedCalculator code to match actual implementation (uses `DoublingFramework` + `FFTOnlyStrategy`)
- Fixes Reference #4: remove wrong link `github.com/ncw/gmp`, replace with correct description or remove
- Replaces "Usage" section CLI examples with benchmark commands

**Step 2: Commit**

```bash
git add Docs/algorithms/FFT.md
git commit -m "docs(algorithms): rewrite FFT.md from scratch

Added complete bigfft file inventory. Fixed wrong reference link.
Updated to 3-tier multiplication. Replaced CLI with Go API."
```

---

## Task 6: Rewrite `Docs/algorithms/GMP.md`

**Files:**
- Modify: `Docs/algorithms/GMP.md`

**Step 1: Write the new GMP.md**

Replace entire file with content that:

- Keeps overview of GMP purpose — accurate
- Keeps installation instructions (apt, brew, dnf) — accurate
- Updates compilation section: note `cmd/fibcalc` doesn't exist, show:
  ```bash
  # Build requires rebuilding the entry point first
  go build -tags gmp -o fibcalc ./cmd/fibcalc
  ```
  With a note that `cmd/fibcalc` needs to be recreated.
- Updates usage section: show Go API instead of CLI:
  ```go
  // GMP auto-registers when built with -tags=gmp
  factory := fibonacci.GlobalFactory()
  calc, _ := factory.Get("gmp")  // available only with gmp build tag
  ```
- Show how to run tests with GMP:
  ```bash
  go test -tags=gmp -v ./internal/fibonacci/
  ```
- Keeps performance notes about CGO overhead — accurate
- Keeps implementation details — accurate

**Step 2: Commit**

```bash
git add Docs/algorithms/GMP.md
git commit -m "docs(algorithms): rewrite GMP.md from scratch

Added Go API usage. Noted cmd/fibcalc doesn't exist.
Added go test -tags=gmp example."
```

---

## Task 7: Rewrite `Docs/algorithms/MATRIX.md`

**Files:**
- Modify: `Docs/algorithms/MATRIX.md`

**Step 1: Write the new MATRIX.md**

Replace entire file with content that:

- Keeps mathematical foundation (Q matrix, formal proof by induction) — all correct
- Keeps mermaid visualization — correct
- Keeps pseudocode — correct
- Updates Go implementation to show actual `MatrixExponentiation` struct and `MatrixFramework`:
  ```go
  type MatrixExponentiation struct{}

  func (c *MatrixExponentiation) CalculateCore(ctx context.Context, reporter ProgressReporter,
      n uint64, opts Options) (*big.Int, error) {
      // Uses MatrixFramework for the exponentiation loop
  }
  ```
- Keeps Strassen algorithm explanation — mathematically correct
- Keeps Strassen mermaid diagram — correct
- Updates symmetric squaring to use actual function names from `matrix_ops.go`
- Updates zero-allocation to mention `matrix_types.go` for `Matrix2x2` type
- Replaces "Usage" CLI examples with Go API and benchmark:
  ```go
  factory := fibonacci.GlobalFactory()
  calc, _ := factory.Get("matrix")
  result, _ := calc.Calculate(ctx, progressChan, 0, n, fibonacci.Options{
      StrassenThreshold: 3072,
  })
  ```
  ```bash
  go test -bench=BenchmarkMatrix -benchmem ./internal/fibonacci/
  ```
- Keeps references — all valid

**Step 2: Commit**

```bash
git add Docs/algorithms/MATRIX.md
git commit -m "docs(algorithms): rewrite MATRIX.md from scratch

Updated to reflect MatrixFramework pattern. Replaced CLI with
Go API and benchmark commands."
```

---

## Task 8: Rewrite `Docs/algorithms/PROGRESS_BAR_ALGORITHM.md`

**Files:**
- Modify: `Docs/algorithms/PROGRESS_BAR_ALGORITHM.md`

**Step 1: Translate from French and rewrite in English**

Replace entire file with English content that:

- Translates all section headers and prose from French to English
- Title: "Progress Bar Algorithm for O(log n) Algorithms"
- Keeps all mathematical content (geometric series model, formulas) — correct
- Updates function signatures to match actual code:
  - `CalcTotalWork(numBits int) float64` — matches
  - `PrecomputePowers4(numBits int) []float64` — update: actual code uses `powersOf4 [64]float64` lookup table and only allocates for numBits > 64
  - `ReportStepProgress(progressReporter ProgressReporter, lastReported *float64, totalWork, workDone float64, i, numBits int, powers []float64) float64` — matches
- Updates `ProgressReporter` type: `type ProgressReporter func(progress float64)` — matches
- Keeps numerical examples — correct
- Keeps edge cases and validation — correct
- Updates "Recommended Tests" to English with `go test` commands
- Keeps "Adaptation for Other Algorithms" section — useful
- Updates file reference at bottom: confirm `internal/fibonacci/progress.go` and `internal/fibonacci/doubling_framework.go`
- Removes French-only text at the very end

**Step 2: Commit**

```bash
git add Docs/algorithms/PROGRESS_BAR_ALGORITHM.md
git commit -m "docs(algorithms): translate and rewrite PROGRESS_BAR_ALGORITHM.md

Translated from French to English. Updated function signatures
to match actual implementation. Kept mathematical model intact."
```

---

## Task 9: Final verification

**Step 1: Grep for stale references across all docs**

Run:
```bash
grep -r "./fibcalc" Docs/
grep -r "cmd/fibcalc" Docs/ | grep -v "doesn't exist" | grep -v "removed" | grep -v "needs to be"
grep -r "Version.*1\.[0-3]\." Docs/
grep -r "Last Updated" Docs/
grep -r "November 2025" Docs/
grep -r "January 2026" Docs/
```

Expected: no matches (all stale references removed).

**Step 2: Grep for French remnants**

Run:
```bash
grep -ri "Algorithme\|Paramètre\|Retour\|Calcul\|Fonction\|Seuil" Docs/algorithms/PROGRESS_BAR_ALGORITHM.md
```

Expected: no matches (all French translated).

**Step 3: Verify all referenced source files exist**

Run:
```bash
for f in internal/fibonacci/calculator.go internal/fibonacci/registry.go internal/fibonacci/strategy.go internal/fibonacci/observer.go internal/fibonacci/observers.go internal/fibonacci/progress.go internal/fibonacci/options.go internal/fibonacci/doubling_framework.go internal/fibonacci/matrix_framework.go internal/fibonacci/matrix_ops.go internal/fibonacci/matrix_types.go internal/fibonacci/constants.go internal/fibonacci/fft.go internal/fibonacci/fft_based.go internal/fibonacci/fastdoubling.go internal/fibonacci/matrix.go internal/bigfft/fft.go internal/bigfft/fft_core.go internal/bigfft/fft_recursion.go internal/bigfft/fft_poly.go internal/bigfft/fft_cache.go internal/bigfft/fermat.go internal/bigfft/karatsuba.go internal/bigfft/pool.go internal/bigfft/allocator.go internal/bigfft/bump.go internal/bigfft/memory_est.go internal/bigfft/scan.go internal/bigfft/arith_amd64.go internal/bigfft/arith_decl.go internal/bigfft/cpu_amd64.go internal/orchestration/interfaces.go internal/orchestration/orchestrator.go internal/cli/presenter.go internal/cli/output.go internal/cli/ui.go internal/cli/progress_eta.go internal/calibration/calibration.go internal/config/config.go internal/errors/errors.go internal/app/lifecycle.go internal/app/version.go internal/ui/colors.go internal/ui/themes.go; do test -f "$f" && echo "OK: $f" || echo "MISSING: $f"; done
```

Expected: all OK, no MISSING.

**Step 4: Commit (if any fixes needed)**

```bash
git add Docs/
git commit -m "docs: fix any remaining issues from verification pass"
```
