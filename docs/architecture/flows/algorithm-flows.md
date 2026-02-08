# Algorithm Computation Flows

| Attribute | Value |
|-----------|-------|
| **Status** | Verified |
| **Type** | Computation Flow |
| **Complexity** | Very High |
| **Diagrams** | [fastdoubling.mermaid](fastdoubling.mermaid), [matrix.mermaid](matrix.mermaid), [fft-pipeline.mermaid](fft-pipeline.mermaid) |

## Overview

FibCalc implements four Fibonacci algorithms, each with different performance characteristics. All share a common small-N optimization path and interface-based strategy selection.

## Quick Reference

| Algorithm | File | Complexity | Best For |
|-----------|------|------------|----------|
| Fast Doubling | `internal/fibonacci/fastdoubling.go` | O(log n) muls | General purpose, n < 100M |
| Matrix Exponentiation | `internal/fibonacci/matrix.go` | O(log n) muls | Verification, comparison |
| FFT-based | `internal/fibonacci/fft_based.go` | O(log n) muls, FFT-only | Very large n (> 500K) |
| GMP | `internal/fibonacci/calculator_gmp.go` | O(log n) muls | Extremely large n (> 100M) |

## Common Fast Path: Small-N Optimization

All calculators share the same entry point via the `FibCalculator` decorator (`internal/fibonacci/calculator.go:58`).

**For n <= 93** (`MaxFibUint64`, line 14):
- The result fits in `uint64`
- `calculateSmall()` (line 184) uses iterative computation
- Bypasses all frameworks, strategies, pools, and observers
- Returns immediately as `*big.Int`

**For n > 93**: Delegates to the `coreCalculator.CalculateCore()` implementation.

## Algorithm 1: Fast Doubling

**Files**: `fastdoubling.go`, `doubling_framework.go`
**Diagram**: [fastdoubling.mermaid](fastdoubling.mermaid)

### Mathematical Identity

Uses the fast doubling identities:
```
F(2k)   = F(k) * [2*F(k+1) - F(k)]
F(2k+1) = F(k)^2 + F(k+1)^2
```

### Execution Flow

1. **Framework** (`internal/fibonacci/doubling_framework.go:20`): `DoublingFramework.ExecuteDoublingLoop()` drives the computation
2. **Bit Iteration**: Scans bits of n from MSB to LSB (O(log n) iterations)
3. **Strategy Selection**: Each step delegates to a `DoublingStepExecutor`
   - **AdaptiveStrategy** (`strategy.go:96`): Selects math/big Karatsuba for small operands, FFT for large ones (threshold: `FFTThreshold`, default 500K bits)
   - **FFTOnlyStrategy** (`strategy.go:127`): Always uses FFT multiplication
   - **KaratsubaStrategy** (`strategy.go:161`): Always uses math/big (for testing)
4. **Parallelization**: When operand bit length exceeds `ParallelThreshold` (default 4096) and total bits > 5M (`ParallelFFTThreshold`), independent multiply/square operations run concurrently via `executeTasks` (`common.go:119`)
5. **Dynamic Thresholds**: Optional `DynamicThresholdManager` (`dynamic_threshold.go:38`) adjusts FFT/parallel thresholds at runtime based on per-iteration timing

### Concurrency Model

- **Task Semaphore** (`common.go:18`): Limits goroutines to `runtime.NumCPU() * 2`
- **FFT Semaphore**: Limits concurrent FFT operations to `runtime.NumCPU()`
- Parallelization disabled for FFT ranges < 5M bits (overhead exceeds benefit)

### Result Extraction (Zero-Copy)

The result is "stolen" from the pooled `CalculationState` (`doubling_framework.go:278`):
- `result := s.FK` — takes the pointer directly
- `s.FK = new(big.Int)` — replaces with fresh instance for pool return
- Avoids O(n) copy of the result big.Int

## Algorithm 2: Matrix Exponentiation

**Files**: `matrix.go`, `matrix_framework.go`, `matrix_ops.go`, `matrix_types.go`
**Diagram**: [matrix.mermaid](matrix.mermaid)

### Mathematical Identity

Uses the matrix identity:
```
| F(n+1)  F(n)   |   | 1  1 |^n
| F(n)    F(n-1) | = | 1  0 |
```

### Execution Flow

1. **Framework** (`internal/fibonacci/matrix_framework.go:16`): `MatrixFramework.ExecuteMatrixLoop()` drives the computation
2. **Binary Exponentiation**: Scans bits of n from LSB to MSB
3. **Matrix Squaring Optimization**: When the matrix is symmetric (which it is for Fibonacci), uses 3 squarings + 1 multiply instead of 4 multiplies
4. **Strassen Switching** (`matrix_ops.go:48-53`): When operand size exceeds `StrassenThreshold` (default 3072), switches from classic 2x2 multiplication (8 big.Int multiplies) to Strassen-Winograd (7 big.Int multiplies)
5. **Big integer multiplication**: Delegates to `Multiplier` interface — uses same FFT/Karatsuba selection as fast doubling

### Result Extraction (Zero-Copy)

Similar steal pattern (`matrix_framework.go:90`): `result := state.res.a`

## Algorithm 3: FFT-Based Fast Doubling

**File**: `fft_based.go`
**Diagram**: [fft-pipeline.mermaid](fft-pipeline.mermaid)

Uses the same fast doubling identities but with `FFTOnlyStrategy` — all multiplications go through the FFT pipeline regardless of operand size. Optimized for very large n where FFT is always faster.

### FFT Multiplication Pipeline (`internal/bigfft/`)

1. **Size Calculation** (`fft.go:193`): `fftSize()` computes the optimal FFT size (next power of 2)
2. **Memory Allocation**: `BumpAllocator` (`bump.go:27`) provides O(1) pointer-bump allocation with zero fragmentation
3. **Polynomial Conversion** (`fft_poly.go:19`): `polyFromNat()` converts `big.Int` to polynomial (split into W-bit limbs, each becoming a Fermat-ring element)
4. **Forward Transform**: `TransformCached()` (`fft_cache.go:305`) checks LRU cache first; on miss, performs Cooley-Tukey butterfly FFT
5. **Pointwise Multiplication**: Fermat ring multiply (mod 2^k + 1) for each coefficient
   - **amd64**: Assembly-optimized `addVV`/`subVV` via `go:linkname` to `math/big` (`arith_amd64.go`)
   - **Generic**: Pure Go fallback (`arith_generic.go`)
6. **Inverse Transform**: Reverse butterfly, scale by 1/N, carry propagation
7. **Result Conversion**: `IntTo()` reassembles polynomial limbs into `big.Int`

### FFT Caching (`internal/bigfft/fft_cache.go`)

- Thread-safe LRU cache (`TransformCache`, line 54)
- Configurable via `TransformCacheConfig` (line 19)
- Stores forward FFT transforms for reuse
- 15-30% speedup for iterative algorithms

### CPU Feature Detection (`internal/bigfft/cpu_amd64.go`)

Runtime detection of AVX2/AVX-512 for vector arithmetic acceleration.

## Algorithm 4: GMP Fast Doubling

**File**: `calculator_gmp.go` (build tag: `gmp`)

- Standalone fast doubling using GMP assembly-optimized arithmetic
- Auto-registers via `init()` when built with `-tags=gmp`
- Does NOT use DoublingFramework, pools, or strategies
- Best for extremely large n (> 100M) where GMP's assembly outperforms pure Go

## Key Thresholds

| Threshold | Default | Purpose | Source |
|-----------|---------|---------|--------|
| `ParallelThreshold` | 4,096 bits | Enable parallel goroutines | `constants.go` |
| `FFTThreshold` | 500,000 bits | Switch Karatsuba to FFT | `constants.go` |
| `StrassenThreshold` | 3,072 bits | Switch classic to Strassen matrix mul | `constants.go` |
| `ParallelFFTThreshold` | 5,000,000 bits | Enable parallel FFT operations | `constants.go` |
| `MaxPooledBitLen` | 100,000,000 bits | Cap for sync.Pool objects | `common.go:39` |
| `MaxFibUint64` | 93 | Iterative fast path cutoff | `calculator.go:14` |

## Object Pool Strategy

- **`CalculationState` pool** (`common.go`): Reuses state objects for doubling iterations
- **`matrixState` pool** (`matrix_types.go`): Reuses matrix state objects
- **`big.Int` pools** (`bigfft/pool.go`): Tiered size-class pools (word slices, fermat slices, nat slices, fftState)
- **Pool cap**: Objects exceeding `MaxPooledBitLen` (100M bits, ~12.5 MB) are not returned to pools to prevent memory bloat
