# FibCalc Architecture Documentation

> Comprehensive architecture documentation for the FibCalc high-performance Fibonacci calculator.
> Generated via automated reverse engineering analysis on 2026-02-08.

## System Overview

**FibCalc** is a high-performance Fibonacci number calculator implemented in Go 1.25+. It supports CLI and interactive TUI modes, with four algorithm implementations (Fast Doubling, Matrix Exponentiation, FFT-based, GMP), adaptive hardware calibration, and extensive concurrency optimization.

| Metric | Value |
|--------|-------|
| Module | `github.com/agbru/fibcalc` |
| Source files | 98 |
| Test files | 86 |
| Lines of Go | ~31,494 |
| Internal packages | 16 |
| Interfaces | 13 |
| Design patterns | 13 |

## Architecture at a Glance

```
User
  │
  ▼
cmd/fibcalc/main.go          ◄── Entry Point
  │
  ▼
internal/app                   ◄── Lifecycle & Mode Dispatch
  │
  ├──► internal/config         ◄── Configuration (flags, env, calibration)
  │
  ├──► internal/orchestration  ◄── Parallel Execution (errgroup)
  │       │
  │       ▼
  │    internal/fibonacci      ◄── Algorithm Implementations
  │       │
  │       ▼
  │    internal/bigfft         ◄── FFT Multiplication Engine
  │
  ├──► internal/cli            ◄── CLI Presentation (spinner, progress)
  │
  ├──► internal/tui            ◄── TUI Dashboard (Bubble Tea)
  │
  └──► internal/calibration    ◄── Hardware-Adaptive Tuning
```

## Documentation Index

### C4 Architecture Diagrams

| Diagram | Description | Format |
|---------|-------------|--------|
| [System Context](system-context.mermaid) | C4 Level 1 — System boundaries and external actors | Mermaid |
| [Container Diagram](container-diagram.mermaid) | C4 Level 2 — Major packages and their relationships | Mermaid |
| [Component Diagram](component-diagram.mermaid) | C4 Level 3 — Interfaces, structs, and dependencies | Mermaid |
| [Dependency Graph](dependency-graph.mermaid) | Package dependency DAG with layer grouping | Mermaid |

### Execution Flows

| Flow | Documentation | Diagram |
|------|--------------|---------|
| CLI Execution | [flows/cli-flow.md](flows/cli-flow.md) | [flows/cli-flow.mermaid](flows/cli-flow.mermaid) |
| TUI Execution | [flows/tui-flow.md](flows/tui-flow.md) | [flows/tui-flow.mermaid](flows/tui-flow.mermaid) |
| Algorithm Computation | [flows/algorithm-flows.md](flows/algorithm-flows.md) | [flows/fastdoubling.mermaid](flows/fastdoubling.mermaid), [flows/matrix.mermaid](flows/matrix.mermaid), [flows/fft-pipeline.mermaid](flows/fft-pipeline.mermaid) |
| Configuration & Calibration | [flows/config-flow.md](flows/config-flow.md) | [flows/config-flow.mermaid](flows/config-flow.mermaid) |

### Design Patterns & Interfaces

| Document | Description |
|----------|-------------|
| [patterns/design-patterns.md](patterns/design-patterns.md) | Catalog of all 13 design patterns with file:line references |
| [patterns/interface-hierarchy.mermaid](patterns/interface-hierarchy.mermaid) | Interface hierarchy and implementation relationships |

### Validation

| Document | Description |
|----------|-------------|
| [validation/validation-report.md](validation/validation-report.md) | Architecture validation: 22 PASS, 0 FAIL, 6 WARNING |

## Package Architecture

### Layer Model

The codebase follows a strict four-layer architecture with no circular dependencies:

| Layer | Packages | Responsibility |
|-------|----------|----------------|
| **Entry** | `cmd/fibcalc` | Binary entry point |
| **Application** | `internal/app`, `internal/config` | Lifecycle, configuration, dispatch |
| **Orchestration** | `internal/orchestration` | Parallel execution, result aggregation |
| **Business** | `internal/fibonacci`, `internal/bigfft`, `internal/calibration` | Algorithms, FFT engine, tuning |
| **Presentation** | `internal/cli`, `internal/tui` | CLI output, TUI dashboard |
| **Support** | `internal/errors`, `internal/format`, `internal/metrics`, `internal/parallel`, `internal/sysmon`, `internal/ui`, `internal/testutil` | Shared utilities (leaf nodes) |

### Package Dependencies

- **Hub package**: `internal/fibonacci` — imported by 5 other packages
- **Composition root**: `internal/app` — 8 internal dependencies
- **Widest fan-out**: `internal/calibration` — 7 internal dependencies
- **Leaf packages** (no internal deps): `bigfft`, `errors`, `format`, `metrics`, `parallel`, `sysmon`, `testutil`, `ui`

## Key Algorithms

| Algorithm | Time Complexity | Best For | File |
|-----------|----------------|----------|------|
| Fast Doubling | O(log n) multiplications | General purpose, n < 100M | `internal/fibonacci/fastdoubling.go` |
| Matrix Exponentiation | O(log n) multiplications | Verification, comparison | `internal/fibonacci/matrix.go` |
| FFT-based | O(log n) FFT multiplications | Very large n (> 500K bits) | `internal/fibonacci/fft_based.go` |
| GMP (optional) | O(log n) GMP multiplications | Extremely large n (> 100M) | `internal/fibonacci/calculator_gmp.go` |

All algorithms share a common fast path: for n <= 93, an iterative uint64 computation is used, bypassing all frameworks and pools.

## Key Thresholds

| Threshold | Default | Purpose |
|-----------|---------|---------|
| `ParallelThreshold` | 4,096 bits | Enable concurrent goroutines |
| `FFTThreshold` | 500,000 bits | Switch from Karatsuba to FFT multiplication |
| `StrassenThreshold` | 3,072 bits | Switch from classic to Strassen matrix multiply |
| `ParallelFFTThreshold` | 5,000,000 bits | Enable parallel FFT operations |
| `MaxPooledBitLen` | 100,000,000 bits | Cap for sync.Pool object retention |
| `MaxFibUint64` | 93 | Iterative fast path cutoff |

Thresholds are resolved via: CLI flags > env vars > calibration profile > adaptive estimation > static defaults.

## Configuration Priority

```
CLI Flags (--parallel-threshold=8192)
    │
    ▼ (override)
Environment Variables (FIBCALC_PARALLEL_THRESHOLD=8192)
    │
    ▼ (override)
Cached Calibration Profile (~/.fibcalc_calibration.json)
    │
    ▼ (override)
Adaptive Hardware Estimation (CPU cores, architecture)
    │
    ▼ (fallback)
Static Defaults (constants.go)
```

## Concurrency Model

- **errgroup**: Orchestrator runs multiple calculators concurrently
- **Task semaphore**: Limits goroutines to `NumCPU * 2` (channel-based)
- **FFT semaphore**: Limits concurrent FFT operations to `NumCPU`
- **ProgressSubject.Freeze()**: Lock-free observer snapshots for hot loops
- **Object pools**: `sync.Pool` with tiered size classes reduces GC pressure
- **Bump allocator**: O(1) allocation for FFT temporaries

## Build Tags & Platform

- **Standard**: `go build ./cmd/fibcalc`
- **GMP**: `go build -tags=gmp ./cmd/fibcalc` (requires libgmp)
- **PGO**: `make build-pgo` (profile at `cmd/fibcalc/default.pgo`)
- **amd64 optimizations**: Assembly via `go:linkname` to `math/big`, AVX2/AVX-512 detection
- **Generic fallback**: Pure Go implementations for non-amd64 platforms

## External Dependencies

| Dependency | Purpose |
|-----------|---------|
| `golang.org/x/sync` | errgroup for concurrent execution |
| `golang.org/x/sys` | Signal handling, platform detection |
| `github.com/rs/zerolog` | Structured logging |
| `github.com/briandowns/spinner` | CLI spinner animation |
| `github.com/shirou/gopsutil/v4` | System CPU/memory metrics (TUI) |
| `github.com/charmbracelet/bubbletea` | TUI framework (Elm architecture) |
| `github.com/charmbracelet/lipgloss` | TUI styling |
| `github.com/charmbracelet/bubbles` | TUI components |
| `github.com/ncw/gmp` | GMP bindings (optional) |
| `go.uber.org/mock` | Mock generation for testing |
| `github.com/leanovate/gopter` | Property-based testing |

## Architectural Decisions & Trade-offs

### Decision 1: Decorator over Inheritance
**Context**: Need to add cross-cutting concerns to algorithm implementations.
**Decision**: `FibCalculator` decorator wraps `coreCalculator` interface.
**Trade-off**: Slightly more indirection, but algorithms remain pure computation without progress/pool concerns.

### Decision 2: Dual Semaphore Strategy
**Context**: Need to limit both total goroutines and FFT-specific parallelism.
**Decision**: Two separate channel-based semaphores with different capacities.
**Trade-off**: More complex than a single limiter, but prevents FFT memory exhaustion while allowing non-FFT work to proceed.

### Decision 3: Bump Allocator for FFT
**Context**: FFT operations need many temporary allocations in a predictable pattern.
**Decision**: Custom bump allocator alongside sync.Pool-based allocator.
**Trade-off**: Arena memory is not released until `Reset()`, but allocation is O(1) with zero fragmentation.

### Decision 4: Observer Freeze for Hot Loops
**Context**: Progress reporting in tight computation loops must not introduce lock contention.
**Decision**: `ProgressSubject.Freeze()` copies the observer slice for lock-free iteration.
**Trade-off**: Snapshot may miss late-registered observers, but eliminates mutex in the hot path.

### Decision 5: Global Factory Singleton
**Context**: GMP calculator uses `init()` for auto-registration.
**Decision**: Package-level `GlobalFactory()` singleton.
**Trade-off**: Global mutable state complicates parallel testing, but enables seamless optional component registration.

## Recommendations for Improvement

1. **Remove dead code**: `RenderBrailleChart`, deprecated `MultiplicationStrategy` alias
2. **Fix documentation drift**: Update CLAUDE.md to remove references to non-existent `formal/` directory and overstated fuzz target counts
3. **Add compile-time interface checks**: `var _ Interface = (*Impl)(nil)` for all observer implementations
4. **Reduce global state**: Consider dependency injection for factory, semaphores, and pools to improve test isolation
5. **Consider removing unused API surface**: `MustGet`, `Has`, `ProgressReporterFunc` if not planned for future use

## Cross-Reference with CLAUDE.md

This architecture documentation is consistent with the existing `CLAUDE.md` project instructions, with the following discrepancies noted in the [validation report](validation/validation-report.md):

- `formal/` directory references in CLAUDE.md do not correspond to files in the repository
- Fuzz target count in CLAUDE.md (17) exceeds actual `Fuzz*` functions found (4)
- Several test file references in CLAUDE.md point to files that don't exist

All other architectural claims in CLAUDE.md were verified as accurate.
