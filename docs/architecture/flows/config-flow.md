# Configuration & Calibration Flow

| Attribute | Value |
|-----------|-------|
| **Status** | Verified |
| **Type** | Configuration Flow |
| **Complexity** | Medium |
| **Diagram** | [config-flow.mermaid](config-flow.mermaid) |

## Overview

FibCalc uses a multi-layered configuration system with five priority levels, hardware-adaptive threshold estimation, and optional runtime dynamic adjustment.

## Flow Boundaries

| Boundary | From | To |
|----------|------|----|
| Parsing | `internal/config` | `internal/app` |
| Calibration | `internal/calibration` | `internal/app` |
| Options | `internal/app` | `internal/fibonacci` |
| Dynamic | `internal/fibonacci` | Runtime adjustment |

## Quick Reference

| Component | File | Line |
|-----------|------|------|
| Config parser | `internal/config/config.go` | 129 |
| Env overrides | `internal/config/env.go` | — |
| Calibration runner | `internal/calibration/runner.go` | — |
| Adaptive estimation | `internal/calibration/adaptive.go` | — |
| Micro-benchmarks | `internal/calibration/microbench.go` | — |
| Profile I/O | `internal/calibration/io.go` | — |
| Options struct | `internal/fibonacci/options.go` | 8 |
| Default constants | `internal/fibonacci/constants.go` | — |
| Dynamic thresholds | `internal/fibonacci/dynamic_threshold.go` | 38 |

## Configuration Priority (Highest to Lowest)

### 1. CLI Flags (Highest Priority)

16 CLI flags parsed via `flag.Parse()`:
- `--n` — Fibonacci number to compute (default: 100,000,000)
- `--algorithm` — Algorithm selection: fast, matrix, fft (default: fast)
- `--compare` — Run all algorithms and compare
- `--parallel-threshold` — Parallel goroutine threshold (0 = auto)
- `--fft-threshold` — FFT multiplication threshold (0 = auto)
- `--strassen-threshold` — Strassen matrix threshold (0 = auto)
- `--timeout` — Calculation timeout duration
- `--tui` — Enable TUI mode
- `--calibrate` — Run full calibration
- `--auto-calibrate` — Run quick calibration
- `--quiet` — Suppress progress output
- `--output` — Write result to file
- And others for logging, cache, dynamic thresholds

### 2. Environment Variables

15 environment variables with `FIBCALC_*` prefix, applied via `applyEnvOverrides()`:
- `FIBCALC_N`, `FIBCALC_ALGORITHM`, `FIBCALC_TIMEOUT`
- `FIBCALC_PARALLEL_THRESHOLD`, `FIBCALC_FFT_THRESHOLD`, `FIBCALC_STRASSEN_THRESHOLD`
- `FIBCALC_TUI`, `FIBCALC_COMPARE`, `FIBCALC_QUIET`
- `FIBCALC_LOG_LEVEL`, `FIBCALC_LOG_FORMAT`
- And others documented in `.env.example`

### 3. Cached Calibration Profile

- Stored at `~/.fibcalc_calibration.json`
- Loaded via `calibration.LoadCachedCalibration()`
- Validated against current CPU model, architecture, and word size
- Stale profiles (different hardware) are ignored

### 4. Adaptive Hardware Estimation

When no valid calibration profile exists:
- `EstimateOptimalParallelThreshold()` — scales by CPU core count
- `EstimateOptimalFFTThreshold()` — varies by architecture (amd64 vs arm64 vs generic)
- `EstimateOptimalStrassenThreshold()` — scales by CPU core count

### 5. Static Defaults (Lowest Priority)

Defined in `internal/fibonacci/constants.go`:
- `DefaultParallelThreshold = 4096`
- `DefaultFFTThreshold = 500,000`
- `DefaultStrassenThreshold = 3072`

Applied by `normalizeOptions()` when `Options` fields are zero.

## Calibration Modes

### Full Calibration (`--calibrate`)

1. Runs comprehensive benchmarks across multiple N values
2. Tests each algorithm with varying thresholds
3. Identifies optimal crossover points
4. Saves results to calibration profile JSON

### Auto-Calibration (`--auto-calibrate`)

1. Runs quick micro-benchmarks (`internal/calibration/microbench.go`)
2. Tests a smaller set of representative workloads
3. Estimates thresholds faster than full calibration
4. Saves results to calibration profile JSON

### Calibration Profile Format

```json
{
  "cpu_model": "...",
  "architecture": "amd64",
  "word_size": 64,
  "parallel_threshold": 4096,
  "fft_threshold": 500000,
  "strassen_threshold": 3072,
  "timestamp": "2025-..."
}
```

## Runtime Dynamic Threshold Adjustment

`DynamicThresholdManager` (`internal/fibonacci/dynamic_threshold.go:38`):

- **Ring buffer**: Stores last 20 `IterationMetric` records
- **Check interval**: Analyzes every 5 iterations
- **Hysteresis**: 15% band to prevent oscillation between strategies
- **Adjustment targets**: FFT threshold and parallel threshold
- **Not exposed via CLI**: Enabled programmatically in Options

### Dynamic Threshold Decision Flow

1. Each iteration records: bit length, duration, whether FFT was used, whether parallelization was used
2. Every 5 iterations, the manager analyzes the ring buffer
3. Compares average duration of FFT vs non-FFT iterations at similar bit lengths
4. If FFT is consistently faster at current threshold - delta, lower the threshold
5. If FFT is consistently slower at current threshold + delta, raise the threshold
6. Hysteresis band prevents thrashing between thresholds

## Options Construction

The `Options` struct (`internal/fibonacci/options.go:8`) flows through:
1. CLI/env values set non-zero fields
2. Calibration profile fills remaining zero fields
3. `normalizeOptions()` fills any remaining zeros from `constants.go` defaults
4. Options are passed to `Calculator.Calculate()` and flow to frameworks and strategies

## Failure Scenarios

| Error | Handling |
|-------|----------|
| Invalid CLI flags | `config.ParseConfig()` returns `ConfigError` (exit 4) |
| Invalid env var format | Logged as warning, env value ignored |
| Corrupt calibration profile | Profile discarded, falls back to adaptive estimation |
| Hardware mismatch in profile | Profile discarded (CPU/arch/word-size validation) |
| Calibration timeout | Partial results used, remaining thresholds use defaults |
