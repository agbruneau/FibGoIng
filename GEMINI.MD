# FibGo: Gemini AI Mandates

This document defines the foundational mandates and architectural principles for the FibGo project. These instructions take absolute precedence over general workflows and tool defaults.

## 1. Project Identity & Mission
FibGo (FibCalc) is a high-performance, "over-engineered" Fibonacci calculator in Go. Its mission is to demonstrate state-of-the-art algorithmic optimizations (Fast Doubling, FFT, Strassen) and software engineering patterns (Clean Architecture, Zero-Allocation, Adaptive Parallelism).

## 2. Core Architectural Principles
- **Clean Architecture**: Strict separation between Business Logic (`internal/fibonacci`, `internal/bigfft`), Orchestration (`internal/orchestration`), and Presentation (`internal/cli`, `internal/tui`).
- **Dependency Rule**: Inner layers (Business) MUST NOT depend on outer layers (Presentation). Use interfaces defined in the orchestration layer (`ProgressReporter`, `ResultPresenter`) for decoupling.
- **Strategy Pattern**: Multiplication strategies (`Adaptive`, `FFTOnly`, `Karatsuba`) are injected into calculation frameworks.

## 3. Engineering Standards
- **Zero-Allocation Strategy**: 
    - Use `sync.Pool` for frequently allocated objects (e.g., `big.Int`, `CalculationState`, `matrixState`).
    - Use `CalculationArena` for contiguous memory allocation in large computations.
    - Prefer `MulTo`/`SqrTo` (destination-passing style) over methods that allocate new objects.
- **Error Handling**: 
    - Use the `internal/errors` package for custom error types (`ConfigError`, `CalculationError`).
    - Standardize exit codes as defined in `internal/errors/handler.go`.
- **Concurrency**:
    - Manage concurrent tasks using the `taskSemaphore` in `internal/fibonacci/common.go`.
    - Use `errgroup` for parallel algorithm execution in `internal/orchestration`.
    - Follow adaptive parallelism thresholds (Parallelism > 4096 bits, FFT > 500k bits).
- **GC Management**: Disable GC during extreme calculations (N ≥ 1M) using `internal/fibonacci/memory/gc_control.go`.

## 4. Testing & Validation
- **Coverage**: Maintain >80% code coverage.
- **Verification**: 
    - Always use golden files (`internal/fibonacci/testdata/fibonacci_golden.json`) for correctness validation.
    - Leverage fuzz testing for edge cases and identity verification.
    - For bug fixes, **empirically reproduce the failure** with a new test case before applying the fix.
- **Benchmarks**: Any performance-sensitive change MUST be accompanied by benchmarks (`go test -bench`).

## 5. Development Workflow
- **Validation Suite**: Always run `make check` (format + lint + test) before considering a task complete.
- **Commit Style**: Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat(bigfft): ...`, `fix(cli): ...`).
- **Tooling**: Prefer project tools (`Makefile`, `golangci-lint`) over manual commands.

## 6. Key Hotspots & Files
- **Algorithm Frameworks**: `internal/fibonacci/doubling_framework.go`, `internal/fibonacci/matrix_framework.go`.
- **Multiplication Engine**: `internal/bigfft/fft_core.go`, `internal/bigfft/fermat.go`.
- **Orchestration**: `internal/orchestration/orchestrator.go`.
- **Adaptive Logic**: `internal/calibration/adaptive.go`, `internal/config/thresholds.go`.

## 7. AI Assistant Specifics
- **Research First**: Before modifying algorithms, read the corresponding deep-dive in `docs/algorithms/`.
- **Efficiency**: When executing batch tasks, prioritize `generalist` delegation for high-volume output or repetitive file edits.
- **No Silent Reverts**: Do not revert changes unless they cause errors or are explicitly requested.
