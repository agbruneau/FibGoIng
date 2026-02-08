# Design Patterns

| Attribute | Value |
|-----------|-------|
| **Status** | Verified |
| **Type** | Pattern Catalog |
| **Count** | 13 patterns identified |
| **Diagram** | [interface-hierarchy.mermaid](interface-hierarchy.mermaid) |

## Overview

FibCalc employs 13 well-known design patterns across its architecture. Each pattern serves a specific purpose in achieving high performance, testability, and clean separation of concerns.

---

## 1. Decorator Pattern

**Purpose**: Add cross-cutting concerns (small-N optimization, progress reporting) without modifying algorithm implementations.

| Item | Location |
|------|----------|
| Decorator | `internal/fibonacci/calculator.go:58` — `FibCalculator` struct |
| Wrapped interface | `internal/fibonacci/calculator.go:48` — `coreCalculator` |
| Public interface | `internal/fibonacci/calculator.go:21` — `Calculator` |
| Small-N fast path | `internal/fibonacci/calculator.go:164` — `if n <= MaxFibUint64` |
| MaxFibUint64 constant | `internal/fibonacci/calculator.go:14` — `const MaxFibUint64 = 93` |
| Observer creation | `internal/fibonacci/calculator.go:137` — `CalculateWithObservers()` |

**How it works**: `FibCalculator` implements `Calculator` by wrapping a `coreCalculator`. Before delegating to the core, it checks if n <= 93 (fits in uint64) and uses an iterative fast path. It also creates and manages `ProgressSubject` for observer-based progress reporting.

---

## 2. Factory Pattern

**Purpose**: Centralized creation of calculator instances with lazy initialization and caching.

| Item | Location |
|------|----------|
| Factory interface | `internal/fibonacci/registry.go:15` — `CalculatorFactory` |
| Default implementation | `internal/fibonacci/registry.go:37` — `DefaultFactory` struct |
| Constructor | `internal/fibonacci/registry.go:53` — `NewDefaultFactory()` |
| Create method | `DefaultFactory.Create()` — lazy creation with caching |

**How it works**: `DefaultFactory` stores creator functions (closures) mapped by name. On first `Create()` call for a name, it invokes the creator, caches the result, and returns it. Subsequent calls return the cached instance.

---

## 3. Registry Pattern

**Purpose**: Global singleton registry with auto-registration for optional components.

| Item | Location |
|------|----------|
| Global factory | `internal/fibonacci/registry.go:227` — `GlobalFactory()` |
| GMP auto-registration | `internal/fibonacci/calculator_gmp.go` — `init()` function |
| Pre-registered algorithms | "fast", "matrix", "fft" in `NewDefaultFactory()` |

**How it works**: `GlobalFactory()` returns a package-level singleton. The `init()` function in `calculator_gmp.go` (compiled only with `-tags=gmp`) automatically registers the GMP calculator on the global factory.

---

## 4. Strategy Pattern + Interface Segregation

**Purpose**: Pluggable multiplication strategies with narrow and wide interfaces following ISP.

| Item | Location |
|------|----------|
| Narrow interface | `internal/fibonacci/strategy.go:29` — `Multiplier` (Multiply, Square, Name) |
| Wide interface | `internal/fibonacci/strategy.go:65` — `DoublingStepExecutor` (extends Multiplier + ExecuteStep) |
| Deprecated alias | `internal/fibonacci/strategy.go:91` — `MultiplicationStrategy` type alias |
| AdaptiveStrategy | `internal/fibonacci/strategy.go:96` — auto-selects math/big vs FFT |
| FFTOnlyStrategy | `internal/fibonacci/strategy.go:127` — always uses FFT |
| KaratsubaStrategy | `internal/fibonacci/strategy.go:161` — always uses math/big |

**How it works**: `Multiplier` is the narrow interface for code that only needs basic multiply/square. `DoublingStepExecutor` extends it with `ExecuteStep()` for optimized doubling steps (e.g., FFT transform reuse). MatrixFramework consumes `Multiplier`; DoublingFramework consumes `DoublingStepExecutor`.

---

## 5. Framework Pattern

**Purpose**: Encapsulate algorithm loop logic, decoupled from multiplication strategies.

| Item | Location |
|------|----------|
| Doubling framework | `internal/fibonacci/doubling_framework.go:20` — `DoublingFramework` |
| Matrix framework | `internal/fibonacci/matrix_framework.go:16` — `MatrixFramework` |

**How it works**: Each framework owns the iteration loop (bit scanning, state management, progress reporting) and delegates arithmetic to pluggable strategies. This avoids duplicating loop logic across algorithm implementations.

---

## 6. Observer Pattern

**Purpose**: Decouple progress reporting from computation.

| Item | Location |
|------|----------|
| Observer interface | `internal/fibonacci/observer.go:16` — `ProgressObserver` |
| Subject | `internal/fibonacci/observer.go:35` — `ProgressSubject` |
| Freeze method | `internal/fibonacci/observer.go:135` — `ProgressSubject.Freeze()` |
| ChannelObserver | `internal/fibonacci/observers.go:19` — bridges to channel-based reporting |
| LoggingObserver | `internal/fibonacci/observers.go:67` — zerolog with throttling |
| NoOpObserver | `internal/fibonacci/observers.go:126` — null object for quiet mode |

**How it works**: `ProgressSubject` maintains a list of observers. `Freeze()` creates a snapshot copy of the observer list for lock-free iteration in hot loops — this avoids mutex contention during the computation-intensive doubling/matrix iterations.

---

## 7. Object Pool Pattern

**Purpose**: Reduce GC pressure by reusing large allocations.

| Item | Location |
|------|----------|
| Word slice pools | `internal/bigfft/pool.go:18` — tiered size classes |
| Fermat pools | `internal/bigfft/pool.go:131` — Fermat number pools |
| Nat slice pools | `internal/bigfft/pool.go:221` — polynomial coefficient pools |
| Fermat slice pools | `internal/bigfft/pool.go:308` — Fermat slice pools |
| FFT state pool | `internal/bigfft/pool.go:405` — combined FFT temporaries |
| Pool cap | `internal/fibonacci/common.go:39` — `MaxPooledBitLen = 100_000_000` |

**How it works**: Multiple `sync.Pool` instances organized by size class. O(1) bitwise index computation selects the appropriate pool. Objects exceeding `MaxPooledBitLen` (100M bits, ~12.5 MB) are not returned to pools to prevent memory bloat.

---

## 8. Bump Allocator Pattern

**Purpose**: O(1) allocation for FFT temporaries with zero fragmentation.

| Item | Location |
|------|----------|
| BumpAllocator struct | `internal/bigfft/bump.go:27` |
| Alloc method | `internal/bigfft/bump.go:104` — `BumpAllocator.Alloc()` |
| TempAllocator interface | `internal/bigfft/allocator.go:10` |

**How it works**: Pre-allocates a contiguous arena. Each `Alloc()` bumps a pointer forward — O(1) with excellent cache locality. `Reset()` rewinds the pointer to reuse the entire arena. Used for FFT polynomial coefficients where allocation patterns are predictable.

---

## 9. LRU Cache Pattern

**Purpose**: Cache FFT forward transforms for reuse across iterations.

| Item | Location |
|------|----------|
| TransformCache struct | `internal/bigfft/fft_cache.go:54` |
| Config | `internal/bigfft/fft_cache.go:19` — `TransformCacheConfig` |
| Cached transform | `internal/bigfft/fft_cache.go:305` — `Poly.TransformCached()` |
| With bump allocator | `internal/bigfft/fft_cache.go:334` — `Poly.TransformCachedWithBump()` |

**How it works**: Thread-safe (RWMutex) LRU cache stores forward FFT transforms keyed by polynomial content. On cache hit, the expensive forward transform is skipped entirely. Provides 15-30% speedup for iterative algorithms that repeatedly transform similar-sized operands.

---

## 10. Adapter Pattern

**Purpose**: Bridge orchestration interfaces to presentation frameworks.

| Item | Location |
|------|----------|
| TUI progress adapter | `internal/tui/bridge.go:32` — `TUIProgressReporter` |
| TUI result adapter | `internal/tui/bridge.go:64` — `TUIResultPresenter` |
| CLI progress reporter | `internal/cli/presenter.go:18` — `CLIProgressReporter` |
| Orchestration interfaces | `internal/orchestration/interfaces.go:19` — `ProgressReporter` |
| Result interface | `internal/orchestration/interfaces.go:58` — `ResultPresenter` |

**How it works**: The orchestration layer depends on abstract `ProgressReporter` and `ResultPresenter` interfaces. CLI and TUI packages provide concrete adapters. The TUI adapter converts method calls to Bubble Tea messages via `program.Send()`.

---

## 11. Null Object Pattern

**Purpose**: Eliminate null checks for optional components.

| Item | Location |
|------|----------|
| NoOpObserver | `internal/fibonacci/observers.go:126` — empty `ProgressObserver` |
| NullProgressReporter | `internal/orchestration/interfaces.go:44` — empty `ProgressReporter` |

**How it works**: Instead of checking `if observer != nil` everywhere, null implementations silently consume all calls. `NoOpObserver` is used for quiet mode and testing. `NullProgressReporter` is used when no progress display is needed.

---

## 12. Zero-Copy Result Return

**Purpose**: Avoid O(n) copy of large Fibonacci results from pooled state.

| Item | Location |
|------|----------|
| Doubling steal | `internal/fibonacci/doubling_framework.go:278` — `result := s.FK` |
| Matrix steal | `internal/fibonacci/matrix_framework.go:90` — `result := state.res.a` |

**How it works**: Instead of copying the result from a pooled state object, the framework "steals" the pointer (`result := s.FK`) and replaces it with a fresh `new(big.Int)` before returning the state to the pool. This avoids an O(n) copy of potentially millions of digits.

---

## 13. Semaphore + Error Collector

**Purpose**: Bounded concurrency with first-error aggregation.

| Item | Location |
|------|----------|
| Task semaphore | `internal/fibonacci/common.go:18` — `chan struct{}` semaphore |
| Semaphore initialization | `internal/fibonacci/common.go:28` — `runtime.NumCPU() * 2` capacity |
| Generic executor | `internal/fibonacci/common.go:119` — `executeTasks[T, PT]()` |
| ErrorCollector | `internal/parallel/errors.go:25` — concurrent error aggregation |

**How it works**: A buffered channel acts as a counting semaphore, limiting concurrent goroutines to `NumCPU * 2`. The generic `executeTasks[T, PT]()` function uses Go generics with a pointer constraint pattern to handle both multiplication and squaring tasks without code duplication. `ErrorCollector` provides thread-safe first-error aggregation for concurrent operations.

---

## Architectural Debt

| Issue | Location | Severity |
|-------|----------|----------|
| Deprecated type alias `MultiplicationStrategy` | `strategy.go:91` | Low — no consumers found |
| Global mutable state (5 singletons) | `registry.go`, `common.go`, `bigfft/pool.go` | Medium — complicates testing |
| Unexported `coreCalculator` in factory | `calculator.go:48` | Low — intentional encapsulation |
| Missing compile-time interface checks | Various observer implementations | Low — would catch regressions |
| Mixed concurrency patterns | `chan struct{}` semaphore vs `errgroup` | Low — both are appropriate for their contexts |
