# IMPROVE.md

Comprehensive improvement backlog for `FibGo` (`/home/agbruneau/FibGo`) based on codebase exploration.

This document is intentionally concrete: every item references specific files, functions, types, or patterns currently present in the repository.

---

## 1) Code Quality & Architecture

### 1.1 Split very large packages into tighter bounded contexts
- **Current state:** `internal/fibonacci/` is very broad (algorithms, orchestration helpers, thresholds, memory, registry, testing helpers, progress aliases).
- **Evidence:** `internal/fibonacci/*.go` plus `internal/fibonacci/memory/*` and `internal/fibonacci/threshold/*`.
- **Improvements:**
  - Extract clearer sub-packages around responsibilities:
    - `internal/fibonacci/algorithm` (fast doubling, matrix, modular)
    - `internal/fibonacci/exec` (framework/step execution)
    - `internal/fibonacci/state` (pool/state management)
  - Keep public surface minimal through a focused facade (`Calculator`, `Factory`, `Options`).

### 1.2 Refactor long multi-responsibility methods
- `internal/fibonacci/doubling_framework.go` → `(*DoublingFramework).ExecuteDoublingLoop` handles:
  - cancellation checks,
  - dynamic threshold adaptation,
  - multiplication dispatch,
  - progress accounting,
  - final state/result extraction.
- `internal/cli/completion.go` is large (`497` lines) and mixes registry + shell-specific rendering logic.
- **Improvements:**
  - Split loop internals into private helpers (`executeStep`, `applyAdditionBit`, `recordDynamicMetrics`, `emitProgress`).
  - Split completion generation into `completion_bash.go`, `completion_zsh.go`, etc.

### 1.3 Remove duplicate helper logic
- Duplicate `preSizeBigInt` appears in:
  - `internal/fibonacci/common.go`
  - `internal/fibonacci/memory/arena.go`
- **Improvements:**
  - Keep a single implementation in `internal/fibonacci/memory` and reuse from callers.
  - Add a unit test covering pre-sizing behavior once.

### 1.4 Clarify process-global mutable state ownership
- Global state patterns exist in:
  - `internal/fibonacci/fastdoubling.go` (`statePool`)
  - `internal/fibonacci/common.go` (`taskSemaphore`)
  - `internal/bigfft/fft_cache.go` (`globalTransformCache`, logger mutation)
- **Improvements:**
  - Add explicit lifecycle docs for each global singleton.
  - Consider dependency-injectable variants for tests/benchmarks.

### 1.5 Improve boundaries between app orchestration and UI concerns
- `internal/app/app.go` and `internal/app/calculate.go` still know concrete CLI/TUI implementations.
- **Improvements:**
  - Introduce small interfaces for rendering and reporting to reduce hard coupling.
  - Keep `Application` assembly in one place, but move mode-specific logic behind abstractions.

---

## 2) Performance

### 2.1 Reduce per-iteration overhead in fast doubling loop
- In `internal/fibonacci/doubling_framework.go`, hot loop repeatedly does context checks and progress accounting.
- **Improvements:**
  - Benchmark checking `ctx.Err()` every N iterations vs every iteration.
  - Optionally gate expensive reporting calculations under progress delta thresholds.

### 2.2 Reduce transient allocations in progress path
- `ExecuteDoublingLoop` computes progress via `CalcTotalWork`, `PrecomputePowers4`, `ReportStepProgress`.
- **Improvements:**
  - Precompute static tables once when feasible (for bounded bit ranges) or pool reusable slices.
  - Benchmark `pprof` allocation profiles for large `n` runs.

### 2.3 Optimize parallel task execution primitives
- `internal/fibonacci/common.go` (`executeParallel3`, `executeTasks`, `executeMixedTasks`) uses goroutine fan-out + semaphore per task.
- **Improvements:**
  - Compare against fixed worker model for repeated 3-operation steps.
  - Add benchmarks isolating semaphore channel overhead vs worker queue.

### 2.4 Strengthen FFT cache memory accounting and limits
- `internal/bigfft/fft_cache.go` uses entry-count based LRU (`MaxEntries`) and `MinBitLen` gating.
- **Improvements:**
  - Add optional **memory-bytes cap** (not only entries).
  - Track approximate bytes per `cacheEntry` and evict by size pressure.
  - Expose stats snapshots (`hits`, `misses`, `evictions`, cache bytes) to diagnostics.

### 2.5 Improve adaptive threshold calibration feedback loop
- Dynamic threshold manager in `internal/fibonacci/threshold/manager.go` uses constants (`FFTSpeedupThreshold`, `ParallelSpeedupThreshold`, etc.).
- **Improvements:**
  - Make hysteresis/speedup constants configurable via `Options` and/or calibration profile.
  - Persist dynamic observations to improve future startup defaults.

### 2.6 Expand PGO workflow coverage
- `Makefile` includes `pgo-profile`, `build-pgo`, cross-platform PGO targets.
- **Improvements:**
  - Include matrix and FFT-heavy benchmark profile generation, not only `BenchmarkFastDoubling`.
  - Add profile freshness checks (warn if profile too old vs git revision).

---

## 3) Testing

### 3.1 Strengthen integration coverage for all runtime modes
- Good coverage exists in unit/property/fuzz tests and an e2e suite (`test/e2e/cli_e2e_test.go`).
- **Improvements:**
  - Add end-to-end scenarios for:
    - `--tui` startup/exit path (`internal/tui/*`)
    - calibration + profile save/load (`internal/calibration/profile.go`, `io.go`)
    - memory-limit and `--last-digits` combined flows (`internal/app/calculate.go`).

### 3.2 Add race-focused tests for public concurrency utilities
- `internal/parallel/errors.go` exposes `ErrorCollector.Reset()` with explicit non-thread-safe warning.
- **Improvements:**
  - Add targeted misuse tests documenting expected behavior/pitfalls.
  - Consider redesign to avoid unsafe reusable API if not needed.

### 3.3 Add fault-injection tests for panic/error boundaries
- `internal/orchestration/orchestrator.go` runs calculators concurrently with `errgroup`; panic containment behavior should be explicit.
- **Improvements:**
  - Add tests for panic in one calculator and expected process behavior.
  - Decide policy: recover + report failure vs hard crash; codify in tests.

### 3.4 Add regression suites for config precedence matrix
- `internal/config/config.go` + `internal/config/env.go` already tested extensively.
- **Improvements:**
  - Add explicit matrix tests for CLI aliases + env var override collisions (`-q` vs `--quiet`, `-o` vs `--output`, etc.).
  - Add negative tests for malformed env values with warning/asserted behavior.

### 3.5 Improve benchmark governance
- Benchmarks exist across `internal/fibonacci` and `internal/bigfft`.
- **Improvements:**
  - Add standardized benchmark targets in CI with historical baseline comparison.
  - Add “no significant regression” guardrails for key workloads.

---

## 4) Documentation

### 4.1 Keep architecture docs tightly synchronized with code
- Documentation is strong: `README.md`, `ARCH.md`, `docs/architecture/*`, `docs/PERFORMANCE.md`, `docs/TESTING.md`, `docs/CALIBRATION.md`.
- **Improvements:**
  - Add a lightweight docs-check task to ensure key docs are updated when touching critical packages (`internal/fibonacci`, `internal/bigfft`, `internal/tui`).

### 4.2 Document operational guidance for heavy workloads
- **Improvements:**
  - Add a practical “production tuning” section in `docs/PERFORMANCE.md`:
    - choosing `--threshold`, `--fft-threshold`, `--memory-limit`, `--timeout`
    - interpreting calibration output.

### 4.3 Improve API discoverability for contributors
- **Improvements:**
  - Add package-level usage examples for:
    - `internal/orchestration.ExecuteCalculations`
    - `internal/fibonacci.NewCalculator`
    - `internal/config.ParseConfig`.

### 4.4 Expand contributor workflow docs
- `CONTRIBUTING.md` already exists and is substantial.
- **Improvements:**
  - Add explicit “architecture hotspots” section pointing to:
    - `internal/fibonacci/doubling_framework.go`
    - `internal/bigfft/fft_cache.go`
    - `internal/tui/model.go`.

---

## 5) Error Handling

### 5.1 Add richer error context for orchestrated runs
- `internal/orchestration/orchestrator.go` stores per-calculator `Err` but errors are mostly opaque strings.
- **Improvements:**
  - Wrap errors with calculator name/index consistently at capture site.
  - Preserve root cause chain for better diagnostics.

### 5.2 Standardize user-facing vs internal error messages
- `internal/errors/errors.go` defines structured types (`ConfigError`, `TimeoutError`, `ValidationError`, `MemoryError`), and `internal/errors/handler.go` formats output.
- **Improvements:**
  - Ensure all command paths route through one central formatting strategy.
  - Add remediation hints in selected user-facing messages (`MemoryError`, config conflicts).

### 5.3 Improve multi-error reporting in config validation
- `internal/config/config.go` `AppConfig.Validate` returns first failure.
- **Improvements:**
  - Support accumulating multiple validation issues and printing them together.
  - Improves UX for users fixing multiple flags/env vars in one pass.

### 5.4 Clarify cancellation semantics end-to-end
- Context cancellation is checked in algorithm loops, but semantics across deeper FFT operations should be explicit.
- **Improvements:**
  - Document and test cancellation propagation from `Application.Run` to calculator internals.

---

## 6) Concurrency & Parallelism

### 6.1 Rationalize concurrency ceilings across layers
- Concurrency controls are layered:
  - fibonacci task semaphore (`internal/fibonacci/common.go`)
  - FFT recursion/parallel internals (`internal/bigfft/*`)
  - algorithm fan-out (`internal/orchestration/orchestrator.go`).
- **Improvements:**
  - Introduce one top-level concurrency budget or coordination strategy to avoid oversubscription.
  - Expose tuning knobs for advanced users.

### 6.2 Add robust backpressure/termination safeguards for progress channel
- `ExecuteCalculations` creates buffered `progressChan` (`ProgressBufferMultiplier`) and display goroutine.
- **Improvements:**
  - Add defensive behavior if consumer fails or exits unexpectedly.
  - Consider context-aware non-blocking progress writes in calculators.

### 6.3 Improve parallel error short-circuiting
- `executeParallel3` waits all goroutines then returns first error.
- **Improvements:**
  - Add cancellation signal to stop peers sooner when one operation fails.
  - Potentially reduce wasted CPU on failed iterations.

### 6.4 Document thread-safety contracts prominently
- `ErrorCollector.Reset()` is unsafe concurrently; cache objects return shared references in `fft_cache.go` (`Get` docs warn not to mutate).
- **Improvements:**
  - Enforce contracts with lint/test patterns where possible.
  - Add stronger comments near call sites, not only type definitions.

---

## 7) Configuration & Tooling

### 7.1 Expand config validation and conflict detection
- `internal/config/config.go` and `internal/config/env.go` already parse many flags/env vars.
- **Improvements:**
  - Validate incompatible combinations (e.g., `--quiet` + interactive expectations, extreme thresholds).
  - Validate ranges for fields like `LastDigits`, threshold values, and memory limits with actionable messages.

### 7.2 Consider optional config file support
- Current model: defaults + env + CLI.
- **Improvements:**
  - Add optional `--config` path (YAML/TOML) merged with existing precedence rules.
  - Useful for reproducible benchmark/calibration runs.

### 7.3 Strengthen build reproducibility
- `Makefile` is strong (cross-build, PGO, lint/security targets).
- **Improvements:**
  - Add reproducible build options and documented release profile.
  - Add a `make verify` meta-target running fmt/lint/test/security in one command.

### 7.4 Improve CI automation alignment with local workflow
- Repository has substantial tests and lint configuration (`.golangci.yml`).
- **Improvements:**
  - Ensure CI pipeline executes key Make targets (`test`, `lint`, `security`, selected benchmarks).
  - Publish coverage and benchmark artifacts.

### 7.5 Harden linter profile over time
- `.golangci.yml` already enables a broad set of linters.
- **Improvements:**
  - Periodically review exclusions and thresholds (`funlen`, complexity limits) to prevent silent drift.

---

## 8) Security

### 8.1 Add explicit resource abuse safeguards
- Heavy computations can consume large CPU/memory for large `n`.
- **Improvements:**
  - Add optional hard cap for `n` (or mandatory confirmation above threshold).
  - Add stronger enforcement path for memory budget beyond warning pathways.

### 8.2 Harden file-path handling for generated artifacts
- User-controlled output/profile paths used in:
  - calibration/profile IO paths (`internal/calibration/profile.go`, `io.go`)
  - output writes in CLI (`internal/cli/output.go`, `internal/app/calculate.go`).
- **Improvements:**
  - Normalize and validate paths.
  - Improve error messages for permission/path traversal edge cases.

### 8.3 Expand supply-chain security posture
- `Makefile` includes `security` target (`gosec`), dependencies listed in `go.mod`/`go.sum`.
- **Improvements:**
  - Add automated dependency update/scanning flow.
  - Add SBOM generation in release pipeline.
  - Add vulnerability check step (e.g., govulncheck) in CI.

### 8.4 Improve security documentation
- **Improvements:**
  - Add `SECURITY.md` with reporting process and supported versions.

---

## 9) Maintainability

### 9.1 Encode rationale for critical constants
- Important constants exist across files, e.g.:
  - `ParallelFFTThreshold` / thresholds (`internal/fibonacci/constants.go`, `fastdoubling.go`)
  - cache defaults (`internal/bigfft/fft_cache.go`).
- **Improvements:**
  - Ensure each has benchmark-backed rationale references (link docs/bench command used).

### 9.2 Consolidate logging strategy
- Structured logging via `zerolog` appears in many internals; user output uses formatted prints in app/cli.
- **Improvements:**
  - Define a logging policy:
    - what goes to logger vs stdout/stderr,
    - correlation fields (algo, n, mode, thresholds),
    - verbosity levels.

### 9.3 Reduce coupling around global package loggers
- Setter-based global loggers in:
  - `fibonacci.SetRegistryLogger`, `fibonacci.SetTaskLogger`, `bigfft.SetCacheLogger` (`internal/app/app.go` wiring).
- **Improvements:**
  - Prefer explicit logger dependency injection to improve test isolation.

### 9.4 Keep long files manageable
- Notable large files:
  - `internal/tui/model.go` (420 lines)
  - `internal/cli/completion.go` (497 lines)
  - `internal/bigfft/fft_cache.go` (496 lines)
- **Improvements:**
  - Split by concern and keep local invariants easier to reason about.

---

## 10) Dependencies & Ecosystem

### 10.1 Revisit Go toolchain target
- `go.mod` currently specifies `go 1.25.0`.
- **Improvements:**
  - Confirm team/runtime compatibility and CI availability for chosen version.
  - Document minimum supported Go version policy.

### 10.2 Classify and prune dependency footprint
- Key direct dependencies include UI stack (`bubbletea`, `bubbles`, `lipgloss`), logging (`zerolog`), property tests (`gopter`), GMP (`github.com/ncw/gmp`), system metrics (`gopsutil`), sync helpers (`x/sync`).
- **Improvements:**
  - Periodic dependency audit:
    - identify optional vs core dependencies,
    - reduce transitive footprint where possible.

### 10.3 Formalize optional feature boundaries
- GMP support appears optional (`internal/fibonacci/calculator_gmp.go`).
- **Improvements:**
  - Make optional features explicit in docs/build flags and CI matrix.
  - Ensure graceful behavior when optional native dependencies are absent.

### 10.4 Expand ecosystem automation
- **Improvements:**
  - Add release automation (checksums, changelog validation, artifact signing if desired).
  - Add compatibility matrix testing (OS/arch combinations already partially represented in `Makefile`).

---

## Suggested Prioritization

### High priority (correctness, safety, operability)
1. Unify/clarify concurrency budgets across fibonacci + FFT + orchestration layers.
2. Strengthen cancellation/error boundary behavior in parallel execution paths.
3. Add stricter resource abuse safeguards for extreme `n` and memory usage.
4. Remove duplicated helper implementations (`preSizeBigInt`) and refactor hot complex loops.

### Medium priority (performance + developer velocity)
1. Decompose large files/functions (`doubling_framework`, `completion`, `tui/model`, `fft_cache`).
2. Expand integration and fault-injection tests around app mode transitions and failures.
3. Add richer cache metrics + memory-bound cache policies.

### Low priority (ecosystem polish)
1. Add `SECURITY.md` and expanded dependency automation.
2. Optional config-file support.
3. Additional docs on advanced tuning and architecture hotspots.

---

## Notes
- This repo already demonstrates strong engineering discipline: comprehensive tests, deep docs, strict linting, calibration tooling, and performance-focused implementation.
- The recommendations above are intended to improve scalability, clarity, and long-term operability as complexity grows.