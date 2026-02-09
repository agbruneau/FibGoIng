# Memory Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce FibGo's peak memory footprint by 30-40% to push the maximum calculable F(N) on 64 Go RAM from ~2-3B to ~5B+.

**Architecture:** Three-pronged approach — (1) reformulate the doubling algebra to reduce live temporaries from 6 to 5 `big.Int`, (2) guarantee in-place buffer reuse in all multiplication paths, (3) add a calculation arena allocator for contiguous pre-allocation. Phase 2 adds GC control and memory monitoring. Phase 3 adds partial-digit calculation for unbounded N.

**Tech Stack:** Go 1.25+, `math/big`, `runtime`, `runtime/debug`, existing `internal/bigfft` and `internal/fibonacci` packages. No new external dependencies.

**Out of Scope:** `--first-digits K` (Binet-based first K digits) is deferred to a future iteration.

---

## Dependency Graph

```
Task 1 (6→5 big.Int)
  ├──→ Task 2 (pre-sizing) ──→ Task 4 (arena)
  └──→ Task 3 (in-place multiply) ──→ Task 4 (arena)
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                     Task 5 (GC control)   Task 7 (modular, independent)
                              │                   │
                              ▼                   ▼
                     Task 6 (monitoring)   Task 8 (memory budget, needs Task 7)
                              │                   │
                              └─────────┬─────────┘
                                        ▼
                               Task 9 (final validation)
```

**Parallelism opportunities for agent teams:**
- Tasks 2 and 3 can run in parallel after Task 1 completes.
- Tasks 5 and 7 can run in parallel after Phase 1 completes.
- Task 6 depends on Task 5 (uses GCStats type).
- Task 8 depends on Task 7 (references `--last-digits`).

**Rollback strategy:** Each task ends with a commit. If tests fail mid-task, run `git checkout -- <modified files>` to restore the last committed state before retrying.

---

## Phase 1 — Fondations Mémoire

### Task 1: Reformulation Algébrique et Réduction des Temporaires (6→5 big.Int)

**Files:**
- Modify: `internal/fibonacci/fastdoubling.go` (CalculationState struct, statePool, AcquireState, ReleaseState, pre-sizing)
- Modify: `internal/fibonacci/doubling_framework.go` (executeDoublingStepMultiplications, loop body)
- Modify: `internal/fibonacci/fft.go` (executeDoublingStepFFT)
- Modify: `internal/fibonacci/fft_test.go` (remove T4 from test state initializations)
- Modify: `internal/fibonacci/fft_race_test.go` (remove T4 from test state initializations)
- Modify: `internal/fibonacci/strategy_test.go` (remove T4 from test state initializations)
- Test: `internal/fibonacci/state_pool_test.go`
- Test: `internal/fibonacci/fastdoubling_test.go`

**Context — Algebraic Reformulation:**

The doubling loop uses 6 `big.Int` (FK, FK1, T1, T2, T3, T4). The current code pre-computes `T4 = 2*FK1 - FK` before ExecuteStep, then uses T4 as a source in the multiplication `T3 = FK × T4`. This requires T4 to survive through ExecuteStep (where T1, T2, T3 are written as destinations), preventing its elimination.

**The fix:** Replace the identity `F(2k) = F(k) × (2F(k+1) - F(k))` with the equivalent `F(2k) = 2·F(k)·F(k+1) - F(k)²`. This eliminates the pre-computation of `2F(k+1)-F(k)` into T4. Instead, ExecuteStep computes three independent multiplications:

```
T3 = FK × FK1      (was: FK × T4)
T2 = FK²
T1 = FK1²
```

Then AFTER ExecuteStep returns, the loop computes:
```
T3 = 2·T3 - T2     → F(2k) = 2·FK·FK1 - FK²
T1 = T1 + T2       → F(2k+1) = FK1² + FK²
```

**Why this is safe for parallel execution:** All three multiplications have independent destinations (T1, T2, T3) and read-only sources (FK, FK1). No data race. The post-multiply arithmetic (shift + subtraction + addition) is O(n/64) — negligible compared to O(n log n) multiplications.

**Bonus:** The FFT path saves one transform (T4's polynomial transform is eliminated), improving performance by ~5-10% for FFT-sized operands.

**Step 1: Write correctness test for modified doubling**

Add to `internal/fibonacci/fastdoubling_test.go`:

```go
// TestFastDoubling_ReducedState_Correctness verifies results are correct
// with the reduced 5-temporary state across key values.
func TestFastDoubling_ReducedState_Correctness(t *testing.T) {
	t.Parallel()

	calc := NewCalculator(&OptimizedFastDoubling{})
	ctx := context.Background()

	cases := []struct {
		n    uint64
		want string
	}{
		{0, "0"},
		{1, "1"},
		{2, "1"},
		{10, "55"},
		{50, "12586269025"},
		{93, "12200160415121876738"},
		{100, "354224848179261915075"},
		{1000, ""},  // verified by golden test
		{10000, ""}, // verified by golden test
	}

	for _, tc := range cases {
		tc := tc
		t.Run(fmt.Sprintf("N=%d", tc.n), func(t *testing.T) {
			t.Parallel()
			result, err := calc.Calculate(ctx, nil, 0, tc.n, Options{})
			if err != nil {
				t.Fatalf("Calculate(%d) error: %v", tc.n, err)
			}
			if tc.want != "" && result.String() != tc.want {
				t.Errorf("Calculate(%d) = %s, want %s", tc.n, result.String(), tc.want)
			}
		})
	}
}
```

Also add the FFT-based test to ensure both code paths are covered:

```go
// TestFFTBased_ReducedState_Correctness verifies FFT-based calculator
// produces correct results with the reduced 5-temporary state.
func TestFFTBased_ReducedState_Correctness(t *testing.T) {
	t.Parallel()

	calc := NewCalculator(&FFTBasedCalculator{})
	ctx := context.Background()

	cases := []struct {
		n    uint64
		want string
	}{
		{0, "0"},
		{1, "1"},
		{10, "55"},
		{100, "354224848179261915075"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(fmt.Sprintf("N=%d", tc.n), func(t *testing.T) {
			t.Parallel()
			result, err := calc.Calculate(ctx, nil, 0, tc.n, Options{})
			if err != nil {
				t.Fatalf("Calculate(%d) error: %v", tc.n, err)
			}
			if tc.want != "" && result.String() != tc.want {
				t.Errorf("Calculate(%d) = %s, want %s", tc.n, result.String(), tc.want)
			}
		})
	}
}
```

**Step 2: Run tests to verify they pass with current code**

Run: `go test -v -run "TestFastDoubling_ReducedState_Correctness|TestFFTBased_ReducedState_Correctness" ./internal/fibonacci/`
Expected: PASS

**Step 3: Modify CalculationState to 5 fields**

In `internal/fibonacci/fastdoubling.go`, change the struct:

```go
// CalculationState aggregates temporary variables for the "Fast Doubling"
// algorithm, allowing efficient management via an object pool.
// Uses 5 big.Int: FK (F(k)), FK1 (F(k+1)), and T1-T3 for
// intermediate multiplication results.
type CalculationState struct {
	FK, FK1, T1, T2, T3 *big.Int
}
```

Update `Reset()` — remove T4 comment:

```go
func (s *CalculationState) Reset() {
	s.FK.SetInt64(0)
	s.FK1.SetInt64(1)
	// T1..T3 are temporaries used as scratch space, so we don't need to clear them.
}
```

Update `statePool`:

```go
var statePool = sync.Pool{
	New: func() any {
		return &CalculationState{
			FK:  new(big.Int),
			FK1: new(big.Int),
			T1:  new(big.Int),
			T2:  new(big.Int),
			T3:  new(big.Int),
		}
	},
}
```

Update `ReleaseState()` to check 5 fields:

```go
func ReleaseState(s *CalculationState) {
	if s == nil {
		return
	}
	if checkLimit(s.FK) || checkLimit(s.FK1) ||
		checkLimit(s.T1) || checkLimit(s.T2) ||
		checkLimit(s.T3) {
		return
	}
	statePool.Put(s)
}
```

Update pre-sizing block in `CalculateCore` — remove `s.T4`:

```go
if n > 10000 {
	estimatedBits := int(float64(n) * 0.694)
	estimatedWords := (estimatedBits + 63) / 64
	preSizeBigInt(s.T1, estimatedWords)
	preSizeBigInt(s.T2, estimatedWords)
	preSizeBigInt(s.T3, estimatedWords)
}
```

**Step 4: Update executeDoublingStepMultiplications**

In `internal/fibonacci/doubling_framework.go`, change `s.T4` to `s.FK1` in all multiply calls.

Parallel path — change the first goroutine:

```go
// 1. T3 = FK * FK1
go func() {
	defer wg.Done()
	if err := ctx.Err(); err != nil {
		ec.SetError(fmt.Errorf("canceled before multiply: %w", err))
		return
	}
	var err error
	// Note: We access s.T3, s.FK, s.FK1 safely because each goroutine
	// operates on disjoint destination sets or reads shared sources
	// (FK, FK1 are read-only here).
	// T3 is destination for this goroutine.
	s.T3, err = strategy.Multiply(s.T3, s.FK, s.FK1, opts)
	if err != nil {
		ec.SetError(fmt.Errorf("parallel multiply FK * FK1 failed: %w", err))
	}
}()
```

The other two goroutines (T1 = FK1², T2 = FK²) remain unchanged.

Sequential path:

```go
// Sequential execution with context checks between multiplications
var err error
s.T3, err = strategy.Multiply(s.T3, s.FK, s.FK1, opts)
if err != nil {
	return fmt.Errorf("multiply FK * FK1 failed: %w", err)
}
if err := ctx.Err(); err != nil {
	return fmt.Errorf("canceled after multiply: %w", err)
}
s.T1, err = strategy.Square(s.T1, s.FK1, opts)
if err != nil {
	return fmt.Errorf("square FK1 failed: %w", err)
}
if err := ctx.Err(); err != nil {
	return fmt.Errorf("canceled after square FK1: %w", err)
}
s.T2, err = strategy.Square(s.T2, s.FK, opts)
if err != nil {
	return fmt.Errorf("square FK failed: %w", err)
}
return nil
```

**Step 5: Update the doubling framework loop body**

In `internal/fibonacci/doubling_framework.go`, replace the loop body (lines ~192-255).

Remove entirely:
- Lines 193-206: The T4 pre-computation (`T4 = 2*FK1 - FK`) and the T1↔T4 capacity swap optimization.

After the `ExecuteStep` call, add the post-multiply arithmetic:

```go
// ExecuteStep computed: T3 = FK×FK1, T2 = FK², T1 = FK1²

// Post-multiply: compute F(2k) and F(2k+1) from the three products.
// F(2k)   = 2·FK·FK1 - FK² = 2·T3 - T2
// F(2k+1) = FK1² + FK²     = T1 + T2
s.T3.Lsh(s.T3, 1)
s.T3.Sub(s.T3, s.T2)
s.T1.Add(s.T1, s.T2)

// Swap the pointers for the next iteration.
// FK becomes F(2k) (from T3), FK1 becomes F(2k+1) (from T1).
// T2 and T3 become the old FK and FK1, now temporaries.
// T1 becomes the old T2 (free).
s.FK, s.FK1, s.T2, s.T3, s.T1 = s.T3, s.T1, s.FK, s.FK1, s.T2
```

Replace the addition step (when bit is set) — use T1 instead of T4:

```go
// Addition Step: If the i-th bit of n is 1, update F(k) and F(k+1)
// F(k) <- F(k+1)
// F(k+1) <- F(k) + F(k+1)
if (n>>uint(i))&1 == 1 {
	// s.T1 temporarily stores the new F(k+1).
	// T1 is free after the rotation (holds old T2).
	s.T1.Add(s.FK, s.FK1)
	// Swap pointers to avoid large allocations:
	// s.FK becomes the old s.FK1
	// s.FK1 becomes the new sum (s.T1)
	// s.T1 becomes the old s.FK, now a temporary
	s.FK, s.FK1, s.T1 = s.FK1, s.T1, s.FK
}
```

**Step 6: Update executeDoublingStepFFT**

In `internal/fibonacci/fft.go`, update `executeDoublingStepFFT` to:
1. Remove the T4 polynomial transform (saves one FFT transform).
2. Change the multiply from `fkPoly × t4Poly` to `fkPoly × fk1Poly`.

Replace the function body. Key changes:

Remove these lines:
```go
// DELETE: pT4 := bigfft.PolyFromInt(s.T4, k, m)
// DELETE: t4Poly, err := pT4.Transform(n)
// DELETE: if err != nil { return err }
```

In the parallel path, change goroutine 1:
```go
go func() {
	if err := ctx.Err(); err != nil {
		resChan <- result{nil, fmt.Errorf("canceled before FFT operation: %w", err)}
		return
	}
	// Changed: use fk1Poly instead of t4Poly (FK×FK1 instead of FK×T4)
	v, err := fkPoly.Mul(&fk1Poly)
	if err != nil {
		resChan <- result{nil, err}
		return
	}
	p, err := v.InvTransform()
	if err != nil {
		resChan <- result{nil, err}
		return
	}
	p.M = m
	resChan <- result{p.IntToBigInt(s.T3), nil}
}()
```

**Note:** `fk1Poly` is now read by two goroutines concurrently (goroutine 1 for Mul, goroutine 2 for Sqr). This is safe because `PolValues.Mul()` and `PolValues.Sqr()` are read-only on their operands — the existing code comment at lines 117-123 already documents this guarantee.

In the sequential path, change:
```go
// Changed: use fk1Poly instead of t4Poly
v1, err := fkPoly.Mul(&fk1Poly)
```

The rest (InvTransform, IntToBigInt destinations) remains unchanged.

**Step 7: Update all test files that reference T4**

Remove `T4: new(big.Int)` or `T4: big.NewInt(0)` from all `CalculationState` initializations in:

- `internal/fibonacci/fft_test.go` — 3 occurrences (lines 22, 45, 68)
- `internal/fibonacci/fft_race_test.go` — 3 occurrences (lines 27, 44, 79). Also update line 44: remove `state.T4 = new(big.Int)` from the loop reset. Also remove the T4 pre-computation at lines 31-33 and 82-83 (`state.T2.Lsh(state.FK1, 1)...`) since ExecuteStep no longer expects T4/T2 to be pre-computed.
- `internal/fibonacci/strategy_test.go` — 2 occurrences (lines 313, 338)

**Step 8: Verify compilation**

Run: `go build ./...`
Expected: Compiles without errors. If any file still references `s.T4`, the compiler will catch it.

**Step 9: Run all tests to verify correctness**

Run: `go test -v -race -cover ./internal/fibonacci/`
Expected: ALL PASS

**Step 10: Run golden tests specifically**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS — all golden values match

**Step 11: Run benchmarks to verify no regression**

Run: `go test -bench=. -benchmem -count=3 ./internal/fibonacci/`
Expected: Similar or better performance, fewer allocs/op

**Step 12: Commit**

```bash
git add internal/fibonacci/fastdoubling.go internal/fibonacci/doubling_framework.go internal/fibonacci/fft.go internal/fibonacci/fft_test.go internal/fibonacci/fft_race_test.go internal/fibonacci/strategy_test.go internal/fibonacci/fastdoubling_test.go
git commit -m "$(cat <<'EOF'
perf(fibonacci): reduce CalculationState from 6 to 5 big.Int temporaries

Reformulate doubling algebra: replace F(2k) = FK×(2FK1-FK) with the
equivalent F(2k) = 2·FK·FK1 - FK². This eliminates T4 entirely:
- ExecuteStep computes T3=FK×FK1, T2=FK², T1=FK1² (3 independent ops)
- Post-multiply: T3=2T3-T2 (F(2k)), T1=T1+T2 (F(2k+1))

Benefits: -17% state memory, no data race in parallel path, saves one
FFT transform in the FFT code path.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Pré-dimensionnement Amélioré des Buffers

**Files:**
- Modify: `internal/fibonacci/fastdoubling.go` (pre-sizing in CalculateCore)
- Modify: `internal/fibonacci/fft_based.go` (add pre-sizing)
- Test: `internal/fibonacci/fastdoubling_test.go`

**Context:** Currently pre-sizing only happens for `n > 10000` and only for T1-T3 (after Task 1). We should (a) lower the threshold to 1000, (b) also pre-size FK and FK1, (c) add pre-sizing to FFTBasedCalculator which currently does none, and (d) use the more precise constant 0.69424.

**Note:** Pre-sizing for `matrixState` (23 `big.Int` in matrix_framework.go) is an optional enhancement. The matrix calculator is rarely used for peak-performance scenarios. If time permits, apply the same pattern there.

**Step 1: Write test to verify pre-sizing is effective**

Add to `internal/fibonacci/fastdoubling_test.go`:

```go
// TestPreSizing_ReducesAllocations verifies pre-sizing doesn't break correctness
// and produces correct results for medium-sized calculations.
func TestPreSizing_ReducesAllocations(t *testing.T) {
	t.Parallel()

	calc := NewCalculator(&OptimizedFastDoubling{})
	ctx := context.Background()

	// Medium-sized calculation that benefits from pre-sizing
	result, err := calc.Calculate(ctx, nil, 0, 50000, Options{})
	if err != nil {
		t.Fatalf("Calculate error: %v", err)
	}
	if result.Sign() <= 0 {
		t.Error("result should be positive")
	}
}
```

**Step 2: Run test**

Run: `go test -v -run TestPreSizing_ReducesAllocations ./internal/fibonacci/`
Expected: PASS

**Step 3: Improve pre-sizing in OptimizedFastDoubling.CalculateCore**

In `internal/fibonacci/fastdoubling.go`, replace the pre-sizing block:

```go
// Pre-size all big.Int buffers based on expected result size.
// F(n) has approximately n * log2(φ) ≈ n * 0.69424 bits.
// Pre-sizing avoids repeated reallocation during the doubling loop.
if n > 1000 {
	estimatedBits := int(float64(n) * 0.69424)
	estimatedWords := (estimatedBits + 63) / 64
	preSizeBigInt(s.FK, estimatedWords)
	preSizeBigInt(s.FK1, estimatedWords)
	preSizeBigInt(s.T1, estimatedWords)
	preSizeBigInt(s.T2, estimatedWords)
	preSizeBigInt(s.T3, estimatedWords)
}
```

**Step 4: Add pre-sizing to FFTBasedCalculator.CalculateCore**

In `internal/fibonacci/fft_based.go`, add pre-sizing before the framework call:

```go
func (c *FFTBasedCalculator) CalculateCore(ctx context.Context, reporter ProgressCallback, n uint64, opts Options) (*big.Int, error) {
	s := AcquireState()
	defer ReleaseState(s)

	// Pre-size buffers for FFT-based calculation
	if n > 1000 {
		estimatedBits := int(float64(n) * 0.69424)
		estimatedWords := (estimatedBits + 63) / 64
		preSizeBigInt(s.FK, estimatedWords)
		preSizeBigInt(s.FK1, estimatedWords)
		preSizeBigInt(s.T1, estimatedWords)
		preSizeBigInt(s.T2, estimatedWords)
		preSizeBigInt(s.T3, estimatedWords)
	}

	// Use framework with FFT-only strategy
	strategy := &FFTOnlyStrategy{}
	framework := NewDoublingFramework(strategy)

	// Execute the doubling loop (no parallelization for FFT-based)
	return framework.ExecuteDoublingLoop(ctx, reporter, n, opts, s, false)
}
```

**Step 5: Verify compilation and run all tests**

Run: `go build ./... && go test -v -race -cover ./internal/fibonacci/`
Expected: ALL PASS

**Step 6: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 7: Commit**

```bash
git add internal/fibonacci/fastdoubling.go internal/fibonacci/fft_based.go internal/fibonacci/fastdoubling_test.go
git commit -m "$(cat <<'EOF'
perf(fibonacci): improve buffer pre-sizing for all calculators

Lower pre-sizing threshold from 10K to 1K, pre-size FK/FK1 (not just
temporaries), add pre-sizing to FFTBasedCalculator, and use the more
precise constant 0.69424 for bit estimation. Reduces reallocation
during the first iterations of the doubling loop.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Multiplications In-Place Garanties

**Files:**
- Modify: `internal/fibonacci/fft.go` (smartMultiply, smartSquare)
- Modify: `internal/bigfft/fft.go` (verify MulTo, SqrTo buffer reuse)
- Test: `internal/fibonacci/fft_test.go`

**Context:** `smartMultiply(z, x, y)` already passes `z` to `math/big.Mul` and `bigfft.MulTo`. But the nil check for `z` happens AFTER the FFT threshold check, meaning the FFT path can receive `z == nil`. We need to ensure z is always initialized before any code path.

**Step 1: Write tests for in-place multiply buffer reuse**

Add to `internal/fibonacci/fft_test.go`:

```go
// TestSmartMultiply_InPlace_BufferReuse verifies that smartMultiply reuses
// the destination buffer when it has sufficient capacity.
func TestSmartMultiply_InPlace_BufferReuse(t *testing.T) {
	t.Parallel()

	x := new(big.Int).SetInt64(123456789)
	y := new(big.Int).SetInt64(987654321)
	expected := new(big.Int).Mul(x, y)

	// Pre-allocate z with sufficient capacity
	z := new(big.Int)
	preSizeBigInt(z, len(expected.Bits())+10)

	result, err := smartMultiply(z, x, y, 0)
	if err != nil {
		t.Fatalf("smartMultiply error: %v", err)
	}
	if result.Cmp(expected) != 0 {
		t.Errorf("smartMultiply = %s, want %s", result.String(), expected.String())
	}
}

// TestSmartMultiply_NilZ verifies that smartMultiply handles nil z.
func TestSmartMultiply_NilZ(t *testing.T) {
	t.Parallel()

	x := new(big.Int).SetInt64(123456789)
	y := new(big.Int).SetInt64(987654321)
	expected := new(big.Int).Mul(x, y)

	result, err := smartMultiply(nil, x, y, 0)
	if err != nil {
		t.Fatalf("smartMultiply error: %v", err)
	}
	if result.Cmp(expected) != 0 {
		t.Errorf("smartMultiply = %s, want %s", result.String(), expected.String())
	}
}

// TestSmartSquare_InPlace_BufferReuse verifies that smartSquare reuses
// the destination buffer when it has sufficient capacity.
func TestSmartSquare_InPlace_BufferReuse(t *testing.T) {
	t.Parallel()

	x := new(big.Int).SetInt64(123456789)
	expected := new(big.Int).Mul(x, x)

	z := new(big.Int)
	preSizeBigInt(z, len(expected.Bits())+10)

	result, err := smartSquare(z, x, 0)
	if err != nil {
		t.Fatalf("smartSquare error: %v", err)
	}
	if result.Cmp(expected) != 0 {
		t.Errorf("smartSquare = %s, want %s", result.String(), expected.String())
	}
}
```

**Step 2: Run tests**

Run: `go test -v -run "TestSmartMultiply_InPlace|TestSmartMultiply_NilZ|TestSmartSquare_InPlace" ./internal/fibonacci/`
Expected: PASS

**Step 3: Move nil check before threshold check in smartMultiply/smartSquare**

In `internal/fibonacci/fft.go`, update `smartMultiply`:

```go
func smartMultiply(z, x, y *big.Int, fftThreshold int) (*big.Int, error) {
	if z == nil {
		z = new(big.Int)
	}

	bx := x.BitLen()
	by := y.BitLen()

	// Tier 1: FFT Multiplication for very large operands
	if fftThreshold > 0 && bx > fftThreshold && by > fftThreshold {
		return bigfft.MulTo(z, x, y)
	}

	// Tier 2: math/big Multiplication (uses optimized algorithms internally)
	return z.Mul(x, y), nil
}
```

Update `smartSquare` similarly:

```go
func smartSquare(z, x *big.Int, fftThreshold int) (*big.Int, error) {
	if z == nil {
		z = new(big.Int)
	}

	bx := x.BitLen()

	// Tier 1: FFT Squaring for very large operands
	if fftThreshold > 0 && bx > fftThreshold {
		return bigfft.SqrTo(z, x)
	}

	// Tier 2: math/big Squaring (uses optimized algorithms internally)
	return z.Mul(x, x), nil
}
```

**Step 4: Investigate bigfft.MulTo buffer reuse**

Read `internal/bigfft/fft.go` to verify `MulTo(z, x, y)` reuses z's backing array when capacity is sufficient. The current implementation passes `z.Bits()` to the FFT core. Verify that:
1. `fftmulTo` checks the destination capacity before allocating.
2. If the capacity is insufficient, it allocates — this is expected and unavoidable.
3. The returned `nat` is set back into z via `z.SetBits(zb)`.

If `fftmulTo` does NOT attempt to reuse the destination buffer, add a capacity check at the top of `MulTo`:
```go
func MulTo(z, x, y *big.Int) (*big.Int, error) {
	if z == nil {
		z = new(big.Int)
	}
	// ... existing implementation
}
```

**Important:** Do NOT modify the FFT core (`fftmulTo`) unless you are certain the change is safe. The FFT buffer management is complex. The primary win here is in `smartMultiply`/`smartSquare` ensuring z is always non-nil.

**Step 5: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./internal/fibonacci/ ./internal/bigfft/`
Expected: ALL PASS

**Step 6: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 7: Commit**

```bash
git add internal/fibonacci/fft.go internal/fibonacci/fft_test.go
git commit -m "$(cat <<'EOF'
perf(fibonacci): guarantee in-place buffer reuse in multiply/square

Move nil-check for z before the FFT threshold check in smartMultiply
and smartSquare, ensuring z is always initialized before any code path.
Eliminates nil-check allocations in hot path.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Arena Allocator pour le Calcul

**Files:**
- Create: `internal/fibonacci/arena.go`
- Create: `internal/fibonacci/arena_test.go`
- Modify: `internal/fibonacci/fastdoubling.go` (integrate arena)
- Modify: `internal/fibonacci/fft_based.go` (integrate arena)

**Context:** The arena pre-allocates a single contiguous block for all `big.Int` backing arrays of a calculation, avoiding per-buffer GC tracking and enabling O(1) bulk release.

**Step 1: Write failing tests for CalculationArena**

Create `internal/fibonacci/arena_test.go`:

```go
package fibonacci

import (
	"math/big"
	"testing"
	"unsafe"
)

func TestCalculationArena_AllocBigInt(t *testing.T) {
	t.Parallel()

	arena := NewCalculationArena(1_000_000) // F(1M)

	z := arena.AllocBigInt(1000)
	if z == nil {
		t.Fatal("AllocBigInt returned nil")
	}
	if cap(z.Bits()) < 1000 {
		t.Errorf("cap(z.Bits()) = %d, want >= 1000", cap(z.Bits()))
	}

	// z should be usable as a normal big.Int
	z.SetInt64(42)
	if z.Int64() != 42 {
		t.Errorf("z = %d, want 42", z.Int64())
	}
}

func TestCalculationArena_MultipleAllocs_NoAliasing(t *testing.T) {
	t.Parallel()

	arena := NewCalculationArena(100_000)

	allocs := make([]*big.Int, 5)
	for i := range allocs {
		allocs[i] = arena.AllocBigInt(100)
		allocs[i].SetInt64(int64(i + 1))
	}

	// All values should be independent (no aliasing)
	for i, z := range allocs {
		if z.Int64() != int64(i+1) {
			t.Errorf("allocs[%d] = %d, want %d", i, z.Int64(), i+1)
		}
	}

	// Verify backing arrays don't overlap
	for i := 0; i < len(allocs); i++ {
		for j := i + 1; j < len(allocs); j++ {
			bi := allocs[i].Bits()
			bj := allocs[j].Bits()
			if cap(bi) > 0 && cap(bj) > 0 {
				// Check that the underlying arrays are disjoint
				pi := unsafe.Pointer(&bi[:cap(bi)][0])
				pj := unsafe.Pointer(&bj[:cap(bj)][0])
				endI := unsafe.Add(pi, uintptr(cap(bi))*unsafe.Sizeof(big.Word(0)))
				endJ := unsafe.Add(pj, uintptr(cap(bj))*unsafe.Sizeof(big.Word(0)))
				if (pi >= pj && pi < endJ) || (pj >= pi && pj < endI) {
					t.Errorf("allocs[%d] and allocs[%d] have overlapping backing arrays", i, j)
				}
			}
		}
	}
}

func TestCalculationArena_Reset(t *testing.T) {
	t.Parallel()

	arena := NewCalculationArena(100_000)

	_ = arena.AllocBigInt(500)
	_ = arena.AllocBigInt(500)

	used := arena.UsedWords()
	if used < 1000 {
		t.Errorf("UsedWords() = %d, want >= 1000", used)
	}

	arena.Reset()

	if arena.UsedWords() != 0 {
		t.Errorf("UsedWords() after Reset = %d, want 0", arena.UsedWords())
	}
}

func TestCalculationArena_Fallback(t *testing.T) {
	t.Parallel()

	// Tiny arena that forces fallback
	arena := NewCalculationArena(10)

	// Request more than arena can hold
	z := arena.AllocBigInt(1_000_000)
	if z == nil {
		t.Fatal("AllocBigInt should fallback to heap, not return nil")
	}
}

func TestCalculationArena_PreSizeFromArena(t *testing.T) {
	t.Parallel()

	arena := NewCalculationArena(100_000)

	z := new(big.Int)
	arena.PreSizeFromArena(z, 500)

	if cap(z.Bits()) < 500 {
		t.Errorf("cap after PreSizeFromArena = %d, want >= 500", cap(z.Bits()))
	}

	// Should be a no-op if already large enough
	arena.PreSizeFromArena(z, 100)
	// No error expected
}
```

**Step 2: Run tests to verify they fail (arena doesn't exist yet)**

Run: `go test -v -run TestCalculationArena ./internal/fibonacci/`
Expected: FAIL — `NewCalculationArena` undefined

**Step 3: Implement CalculationArena**

Create `internal/fibonacci/arena.go`:

```go
package fibonacci

import "math/big"

// CalculationArena pre-allocates a contiguous block of big.Word memory
// for all big.Int temporaries in a Fibonacci calculation. This eliminates
// per-buffer GC tracking and enables O(1) bulk release via Reset().
//
// The arena uses a bump-pointer allocation strategy: each AllocBigInt
// call advances the offset pointer. When capacity is exhausted, it falls
// back to standard heap allocation.
type CalculationArena struct {
	buf    []big.Word
	offset int
}

// NewCalculationArena creates an arena sized for F(n).
// It estimates the total memory needed for 10 big.Int temporaries
// (5 state + 5 margin for multiplications) of size ≈ n × 0.69424 bits.
func NewCalculationArena(n uint64) *CalculationArena {
	if n < 1000 {
		return &CalculationArena{}
	}
	estimatedBits := float64(n) * 0.69424
	wordsPerInt := int(estimatedBits/64) + 1
	totalWords := wordsPerInt * 10 // 5 state + 5 margin
	return &CalculationArena{
		buf: make([]big.Word, totalWords),
	}
}

// AllocBigInt returns a new big.Int whose backing array is allocated from
// the arena. If the arena is exhausted, falls back to heap allocation.
func (a *CalculationArena) AllocBigInt(words int) *big.Int {
	if words <= 0 {
		return new(big.Int)
	}
	z := new(big.Int)
	if a.buf == nil || a.offset+words > len(a.buf) {
		// Fallback: allocate from heap
		buf := make([]big.Word, 0, words)
		z.SetBits(buf)
		return z
	}
	slice := a.buf[a.offset : a.offset+words : a.offset+words]
	a.offset += words
	z.SetBits(slice[:0]) // length 0, capacity words — z is 0
	return z
}

// PreSizeFromArena sets z's backing array to a slice from the arena.
// If the arena is exhausted, falls back to preSizeBigInt.
func (a *CalculationArena) PreSizeFromArena(z *big.Int, words int) {
	if z == nil || words <= 0 {
		return
	}
	if cap(z.Bits()) >= words {
		return // already large enough
	}
	if a.buf != nil && a.offset+words <= len(a.buf) {
		slice := a.buf[a.offset : a.offset+words : a.offset+words]
		a.offset += words
		z.SetBits(slice[:0])
	} else {
		preSizeBigInt(z, words)
	}
}

// Reset resets the arena for reuse without freeing the backing block.
// All previously allocated big.Int values become invalid after Reset.
func (a *CalculationArena) Reset() {
	a.offset = 0
}

// UsedWords returns the number of words currently allocated from the arena.
func (a *CalculationArena) UsedWords() int {
	return a.offset
}

// CapacityWords returns the total capacity of the arena in words.
func (a *CalculationArena) CapacityWords() int {
	return len(a.buf)
}
```

**Step 4: Run arena tests**

Run: `go test -v -run TestCalculationArena ./internal/fibonacci/`
Expected: ALL PASS

**Step 5: Integrate arena into OptimizedFastDoubling.CalculateCore**

In `internal/fibonacci/fastdoubling.go`, modify `CalculateCore` to use the arena for pre-sizing:

```go
func (fd *OptimizedFastDoubling) CalculateCore(ctx context.Context, reporter ProgressCallback, n uint64, opts Options) (*big.Int, error) {
	s := AcquireState()
	defer ReleaseState(s)

	// Create arena for contiguous memory allocation
	arena := NewCalculationArena(n)

	// Pre-size all big.Int buffers from the arena
	if n > 1000 {
		estimatedBits := int(float64(n) * 0.69424)
		estimatedWords := (estimatedBits + 63) / 64
		arena.PreSizeFromArena(s.FK, estimatedWords)
		arena.PreSizeFromArena(s.FK1, estimatedWords)
		arena.PreSizeFromArena(s.T1, estimatedWords)
		arena.PreSizeFromArena(s.T2, estimatedWords)
		arena.PreSizeFromArena(s.T3, estimatedWords)
	}

	// ... rest unchanged (normalizeOptions, framework creation, ExecuteDoublingLoop)
```

**Step 6: Integrate arena into FFTBasedCalculator.CalculateCore**

Same pattern in `internal/fibonacci/fft_based.go`:

```go
func (c *FFTBasedCalculator) CalculateCore(ctx context.Context, reporter ProgressCallback, n uint64, opts Options) (*big.Int, error) {
	s := AcquireState()
	defer ReleaseState(s)

	// Create arena for contiguous memory allocation
	arena := NewCalculationArena(n)

	// Pre-size buffers from the arena
	if n > 1000 {
		estimatedBits := int(float64(n) * 0.69424)
		estimatedWords := (estimatedBits + 63) / 64
		arena.PreSizeFromArena(s.FK, estimatedWords)
		arena.PreSizeFromArena(s.FK1, estimatedWords)
		arena.PreSizeFromArena(s.T1, estimatedWords)
		arena.PreSizeFromArena(s.T2, estimatedWords)
		arena.PreSizeFromArena(s.T3, estimatedWords)
	}

	// Use framework with FFT-only strategy
	strategy := &FFTOnlyStrategy{}
	framework := NewDoublingFramework(strategy)

	// Execute the doubling loop (no parallelization for FFT-based)
	return framework.ExecuteDoublingLoop(ctx, reporter, n, opts, s, false)
}
```

**Step 7: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./internal/fibonacci/`
Expected: ALL PASS

**Step 8: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 9: Run benchmarks**

Run: `go test -bench=BenchmarkFastDoubling -benchmem -count=3 ./internal/fibonacci/`
Expected: Fewer allocs/op, similar or better ns/op

**Step 10: Commit**

```bash
git add internal/fibonacci/arena.go internal/fibonacci/arena_test.go internal/fibonacci/fastdoubling.go internal/fibonacci/fft_based.go
git commit -m "$(cat <<'EOF'
perf(fibonacci): add CalculationArena for contiguous memory allocation

Pre-allocates a single block for all big.Int backing arrays, reducing
GC pressure and memory fragmentation. Falls back to heap allocation
when the arena is exhausted. Includes aliasing safety test.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Contrôle et Monitoring

### Task 5: Contrôle du GC pendant le Calcul

**Files:**
- Create: `internal/fibonacci/gc_control.go`
- Create: `internal/fibonacci/gc_control_test.go`
- Modify: `internal/fibonacci/calculator.go` (integrate GCController)
- Modify: `internal/fibonacci/options.go` (add GCMode field)
- Modify: `internal/config/config.go` (add GCControl flag)

**Step 1: Write failing test for GCController**

Create `internal/fibonacci/gc_control_test.go`:

```go
package fibonacci

import (
	"testing"
)

func TestGCController_Disabled(t *testing.T) {
	t.Parallel()

	gc := NewGCController("disabled", 1_000_000)
	gc.Begin()
	defer gc.End()
	// Should be a no-op — no GC changes
}

func TestGCController_Auto_SmallN(t *testing.T) {
	t.Parallel()

	gc := NewGCController("auto", 100)
	gc.Begin()
	defer gc.End()
	// Should not change GC settings for small N (below threshold)
	if gc.active {
		t.Error("GC controller should not be active for small N")
	}
}

func TestGCController_Auto_LargeN(t *testing.T) {
	t.Parallel()

	gc := NewGCController("auto", 2_000_000)
	if !gc.active {
		t.Error("GC controller should be active for N >= 1M in auto mode")
	}
	gc.Begin()
	defer gc.End()
}

func TestGCController_Aggressive(t *testing.T) {
	t.Parallel()

	gc := NewGCController("aggressive", 100)
	if !gc.active {
		t.Error("GC controller should be active in aggressive mode regardless of N")
	}
	gc.Begin()
	defer gc.End()
}

func TestGCController_Stats_BeforeBegin(t *testing.T) {
	t.Parallel()

	gc := NewGCController("disabled", 100)
	stats := gc.Stats()
	// Before Begin/End, stats should be zero-valued
	if stats.TotalAlloc != 0 {
		t.Errorf("TotalAlloc before Begin should be 0, got %d", stats.TotalAlloc)
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `go test -v -run TestGCController ./internal/fibonacci/`
Expected: FAIL — `NewGCController` undefined

**Step 3: Implement GCController**

Create `internal/fibonacci/gc_control.go`:

```go
package fibonacci

import (
	"math"
	"runtime"
	"runtime/debug"
)

// GCMode controls the garbage collector behavior during calculation.
type GCMode string

const (
	GCModeAuto       GCMode = "auto"
	GCModeAggressive GCMode = "aggressive"
	GCModeDisabled   GCMode = "disabled"
)

// GCAutoThreshold is the minimum N for auto GC control to activate.
const GCAutoThreshold uint64 = 1_000_000

// GCController manages Go's garbage collector during intensive calculations.
// It disables GC during computation and restores it afterward, reducing
// pause times and memory overhead for large calculations.
type GCController struct {
	mode              GCMode
	originalGCPercent int
	active            bool
	startStats        runtime.MemStats
	endStats          runtime.MemStats
}

// GCStats holds GC statistics for a calculation.
type GCStats struct {
	HeapAlloc    uint64
	TotalAlloc   uint64
	NumGC        uint32
	PauseTotalNs uint64
}

// NewGCController creates a GC controller for the given mode and N.
func NewGCController(mode string, n uint64) *GCController {
	gc := &GCController{mode: GCMode(mode)}
	switch gc.mode {
	case GCModeAggressive:
		gc.active = true
	case GCModeAuto:
		gc.active = n >= GCAutoThreshold
	default:
		gc.active = false
	}
	return gc
}

// Begin disables GC if the controller is active.
func (gc *GCController) Begin() {
	if !gc.active {
		return
	}
	runtime.ReadMemStats(&gc.startStats)
	gc.originalGCPercent = debug.SetGCPercent(-1)
	// Set soft memory limit as OOM safety net.
	// Allow up to 3x current memory usage to accommodate large calculations.
	if gc.startStats.Sys > 0 {
		limit := int64(float64(gc.startStats.Sys) * 3)
		if limit > 0 {
			debug.SetMemoryLimit(limit)
		}
	}
}

// End restores original GC settings and triggers a collection.
func (gc *GCController) End() {
	if !gc.active {
		return
	}
	runtime.ReadMemStats(&gc.endStats)
	debug.SetGCPercent(gc.originalGCPercent)
	debug.SetMemoryLimit(math.MaxInt64)
	runtime.GC()
}

// Stats returns GC statistics delta between Begin and End.
// Must be called after End().
func (gc *GCController) Stats() GCStats {
	return GCStats{
		HeapAlloc:    gc.endStats.HeapAlloc,
		TotalAlloc:   gc.endStats.TotalAlloc - gc.startStats.TotalAlloc,
		NumGC:        gc.endStats.NumGC - gc.startStats.NumGC,
		PauseTotalNs: gc.endStats.PauseTotalNs - gc.startStats.PauseTotalNs,
	}
}
```

**Step 4: Run tests**

Run: `go test -v -run TestGCController ./internal/fibonacci/`
Expected: ALL PASS

**Step 5: Add GCMode to Options**

In `internal/fibonacci/options.go`, add to the `Options` struct:

```go
// GCMode controls the garbage collector during calculation.
// Valid values: "auto" (default), "aggressive", "disabled".
GCMode string
```

**Step 6: Add --gc-control flag to config**

In `internal/config/config.go`, add to `AppConfig`:

```go
// GCControl sets the GC control mode ("auto", "aggressive", "disabled").
GCControl string
```

And in the flag definitions section of `ParseConfig`:

```go
fs.StringVar(&config.GCControl, "gc-control", "auto", "GC control during calculation (auto, aggressive, disabled).")
```

**Step 7: Integrate GCController into FibCalculator.CalculateWithObservers**

In `internal/fibonacci/calculator.go`, add GC control at the top of `CalculateWithObservers`:

```go
func (c *FibCalculator) CalculateWithObservers(ctx context.Context, subject *ProgressSubject, calcIndex int, n uint64, opts Options) (result *big.Int, err error) {
	// GC control for large calculations
	gcMode := opts.GCMode
	if gcMode == "" {
		gcMode = "auto"
	}
	gcCtrl := NewGCController(gcMode, n)
	gcCtrl.Begin()
	defer gcCtrl.End()

	// ... existing calculation logic (start timer, freeze observers, etc.)
```

**Step 8: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./...`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add internal/fibonacci/gc_control.go internal/fibonacci/gc_control_test.go internal/fibonacci/options.go internal/fibonacci/calculator.go internal/config/config.go
git commit -m "$(cat <<'EOF'
perf(fibonacci): add GC controller for large calculations

Disables GC during computation for N >= 1M (auto mode), reducing pause
times and ~2x memory overhead from GC scanning. Sets soft memory limit
(3x current Sys) as OOM safety net. Restores GC and runs collection
after calculation. Only calls ReadMemStats when active.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Monitoring Mémoire (CLI + TUI)

**Files:**
- Create: `internal/metrics/memory.go`
- Create: `internal/metrics/memory_test.go`
- Modify: `internal/tui/metrics.go` (add memory details)
- Modify: `internal/cli/presenter.go` (add memory summary)

**Step 1: Write test for MemoryCollector**

Create `internal/metrics/memory_test.go`:

```go
package metrics

import "testing"

func TestMemoryCollector_Snapshot(t *testing.T) {
	t.Parallel()

	mc := NewMemoryCollector()
	snap := mc.Snapshot()

	if snap.HeapAlloc == 0 {
		t.Error("HeapAlloc should be > 0")
	}
	if snap.Sys == 0 {
		t.Error("Sys should be > 0")
	}
}

func TestMemoryCollector_Delta(t *testing.T) {
	t.Parallel()

	mc := NewMemoryCollector()
	before := mc.Snapshot()

	// Allocate some memory
	_ = make([]byte, 1024*1024) // 1 MB

	after := mc.Snapshot()

	// TotalAlloc should be monotonically increasing
	if after.Sys < before.Sys {
		t.Error("Sys should not decrease between snapshots")
	}
}
```

**Step 2: Implement MemoryCollector**

Create `internal/metrics/memory.go`:

```go
package metrics

import "runtime"

// MemorySnapshot holds a point-in-time memory reading.
type MemorySnapshot struct {
	HeapAlloc    uint64 // bytes in use by application
	HeapSys      uint64 // bytes obtained from OS for heap
	Sys          uint64 // total bytes obtained from OS
	NumGC        uint32 // number of completed GC cycles
	PauseTotalNs uint64 // cumulative GC pause time
	HeapObjects  uint64 // number of allocated heap objects
}

// MemoryCollector reads runtime memory statistics.
type MemoryCollector struct{}

// NewMemoryCollector creates a new memory collector.
func NewMemoryCollector() *MemoryCollector {
	return &MemoryCollector{}
}

// Snapshot reads current memory statistics.
func (mc *MemoryCollector) Snapshot() MemorySnapshot {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	return MemorySnapshot{
		HeapAlloc:    m.HeapAlloc,
		HeapSys:      m.HeapSys,
		Sys:          m.Sys,
		NumGC:        m.NumGC,
		PauseTotalNs: m.PauseTotalNs,
		HeapObjects:  m.HeapObjects,
	}
}
```

**Step 3: Run test**

Run: `go test -v -run TestMemoryCollector ./internal/metrics/`
Expected: PASS

**Step 4: Add memory display to TUI metrics panel**

In `internal/tui/metrics.go`, add fields to `MetricsModel`:

```go
heapSys      uint64
heapObjects  uint64
pauseTotalNs uint64
```

Extend the `View()` method to display heap active/total and GC pause info:

```go
// Memory line with heap details (replace existing memory line)
heapStr := metricValueStyle.Render(formatBytes(m.alloc) + " / " + formatBytes(m.heapSys))
gcPauseStr := metricValueStyle.Render(fmt.Sprintf("%d (%.1fms)", m.numGC, float64(m.pauseTotalNs)/1e6))
topLine := fmt.Sprintf("  %s %s | %s %s",
	metricLabelStyle.Render("Heap:"), heapStr,
	metricLabelStyle.Render("GC:"), gcPauseStr)
```

Update the `Update()` method to populate the new fields from the system monitor tick.

**Step 5: Add memory summary to CLI presenter**

In `internal/cli/presenter.go`, add a function to display GC stats after calculation:

```go
// DisplayMemoryStats shows memory statistics after a calculation.
// Called when --details flag is set.
func DisplayMemoryStats(heapAlloc, totalAlloc uint64, numGC uint32, pauseTotalNs uint64, out io.Writer) {
	fmt.Fprintf(out, "\nMemory Stats:\n")
	fmt.Fprintf(out, "  Peak heap:       %s\n", FormatBytes(heapAlloc))
	fmt.Fprintf(out, "  Total allocated: %s\n", FormatBytes(totalAlloc))
	fmt.Fprintf(out, "  GC cycles:       %d\n", numGC)
	if pauseTotalNs > 0 {
		fmt.Fprintf(out, "  GC pause total:  %.2fms\n", float64(pauseTotalNs)/1e6)
	} else {
		fmt.Fprintf(out, "  GC pause total:  0ms (GC disabled)\n")
	}
}
```

**Note:** Check if `FormatBytes` already exists in the `cli` or `format` package. If not, add a helper using the existing `format` package conventions. If `formatBytes` exists as unexported, use it or export it.

**Step 6: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./...`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add internal/metrics/memory.go internal/metrics/memory_test.go internal/tui/metrics.go internal/cli/presenter.go
git commit -m "$(cat <<'EOF'
feat(metrics): add memory monitoring to TUI and CLI

Display heap allocation, GC cycles, and pause times in TUI metrics
panel and CLI post-calculation summary. Uses runtime.ReadMemStats
for point-in-time snapshots.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Modes Avancés

### Task 7: Fast Doubling Modulaire (Derniers Chiffres)

**Files:**
- Create: `internal/fibonacci/modular.go`
- Create: `internal/fibonacci/modular_test.go`
- Modify: `internal/config/config.go` (add --last-digits flag)
- Modify: `internal/app/app.go` (handle partial mode)
- Modify: `internal/fibonacci/fibonacci_fuzz_test.go` (add fuzz target)

**Step 1: Write failing test for modular Fibonacci**

Create `internal/fibonacci/modular_test.go`:

```go
package fibonacci

import (
	"context"
	"fmt"
	"math/big"
	"testing"
)

func TestFastDoublingMod_KnownValues(t *testing.T) {
	t.Parallel()

	cases := []struct {
		n    uint64
		mod  int64
		want int64
	}{
		{0, 1000, 0},
		{1, 1000, 1},
		{10, 1000, 55},
		{100, 10000, 5075},      // F(100) mod 10000 = 5075
		{1000, 1000000, 228875}, // F(1000) last 6 digits
	}

	for _, tc := range cases {
		tc := tc
		t.Run(fmt.Sprintf("N=%d_mod_%d", tc.n, tc.mod), func(t *testing.T) {
			t.Parallel()
			m := big.NewInt(tc.mod)
			result, err := FastDoublingMod(tc.n, m)
			if err != nil {
				t.Fatalf("FastDoublingMod error: %v", err)
			}
			if result.Int64() != tc.want {
				t.Errorf("FastDoublingMod(%d, %d) = %d, want %d",
					tc.n, tc.mod, result.Int64(), tc.want)
			}
		})
	}
}

func TestFastDoublingMod_ConsistentWithFull(t *testing.T) {
	t.Parallel()

	// Compute F(500) fully, then verify last 100 digits match modular result
	calc := NewCalculator(&OptimizedFastDoubling{})
	ctx := context.Background()
	full, err := calc.Calculate(ctx, nil, 0, 500, Options{})
	if err != nil {
		t.Fatalf("full Calculate error: %v", err)
	}

	mod := new(big.Int).Exp(big.NewInt(10), big.NewInt(100), nil) // 10^100
	expected := new(big.Int).Mod(full, mod)

	result, err := FastDoublingMod(500, mod)
	if err != nil {
		t.Fatalf("FastDoublingMod error: %v", err)
	}

	if result.Cmp(expected) != 0 {
		t.Errorf("modular result doesn't match full: got %s, want %s",
			result.String(), expected.String())
	}
}

func TestFastDoublingMod_InvalidModulus(t *testing.T) {
	t.Parallel()

	_, err := FastDoublingMod(10, nil)
	if err == nil {
		t.Error("expected error for nil modulus")
	}

	_, err = FastDoublingMod(10, big.NewInt(0))
	if err == nil {
		t.Error("expected error for zero modulus")
	}

	_, err = FastDoublingMod(10, big.NewInt(-5))
	if err == nil {
		t.Error("expected error for negative modulus")
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `go test -v -run TestFastDoublingMod ./internal/fibonacci/`
Expected: FAIL — `FastDoublingMod` undefined

**Step 3: Implement FastDoublingMod**

Create `internal/fibonacci/modular.go`:

```go
package fibonacci

import (
	"fmt"
	"math/big"
	"math/bits"
)

// FastDoublingMod computes F(n) mod m using the fast doubling algorithm.
// Memory usage is O(log(m)) regardless of n, making it suitable for
// computing the last K digits of F(n) for arbitrarily large n.
//
// Uses the identities:
//
//	F(2k)   = F(k) * (2*F(k+1) - F(k))  mod m
//	F(2k+1) = F(k+1)² + F(k)²            mod m
func FastDoublingMod(n uint64, m *big.Int) (*big.Int, error) {
	if m == nil || m.Sign() <= 0 {
		return nil, fmt.Errorf("modulus must be positive")
	}

	if n == 0 {
		return big.NewInt(0), nil
	}

	fk := big.NewInt(0)  // F(k)
	fk1 := big.NewInt(1) // F(k+1)
	t1 := new(big.Int)   // temporary
	t2 := new(big.Int)   // temporary

	numBits := bits.Len64(n)

	for i := numBits - 1; i >= 0; i-- {
		// F(2k) = F(k) * (2*F(k+1) - F(k)) mod m
		t1.Lsh(fk1, 1)
		t1.Sub(t1, fk)
		t1.Mod(t1, m)
		// Handle negative mod result
		if t1.Sign() < 0 {
			t1.Add(t1, m)
		}
		t1.Mul(t1, fk)
		t1.Mod(t1, m)

		// F(2k+1) = F(k+1)² + F(k)² mod m
		t2.Mul(fk1, fk1)
		fk.Mul(fk, fk)
		t2.Add(t2, fk)
		t2.Mod(t2, m)

		// Assign
		fk.Set(t1)
		fk1.Set(t2)

		// If bit is set: shift to F(2k+1), F(2k+2)
		if (n>>uint(i))&1 == 1 {
			t1.Add(fk, fk1)
			t1.Mod(t1, m)
			fk.Set(fk1)
			fk1.Set(t1)
		}
	}

	return fk, nil
}
```

**Step 4: Run tests**

Run: `go test -v -run TestFastDoublingMod ./internal/fibonacci/`
Expected: ALL PASS

**Step 5: Add --last-digits flag to config**

In `internal/config/config.go`, add to `AppConfig`:

```go
// LastDigits, if > 0, computes only the last K decimal digits of F(N).
// Uses O(K) memory via modular arithmetic.
LastDigits int
```

Add flag in `ParseConfig`:

```go
fs.IntVar(&config.LastDigits, "last-digits", 0, "Compute only the last K decimal digits (uses O(K) memory).")
```

**Step 6: Handle partial mode in app.go**

In `internal/app/app.go`, add dispatch for `--last-digits` mode at the top of `runCalculate`:

```go
func (a *Application) runCalculate(ctx context.Context, out io.Writer) int {
	// Partial computation mode: last K digits only
	if a.Config.LastDigits > 0 {
		return a.runLastDigits(ctx, out)
	}

	// ... existing code ...
```

Implement `runLastDigits`:

```go
// runLastDigits computes the last K digits of F(N) using modular arithmetic.
func (a *Application) runLastDigits(ctx context.Context, out io.Writer) int {
	k := a.Config.LastDigits
	n := a.Config.N

	if !a.Config.Quiet {
		fmt.Fprintf(out, "Computing last %d digits of F(%d) using modular arithmetic...\n", k, n)
	}

	// m = 10^K
	m := new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(k)), nil)

	start := time.Now()
	result, err := fibonacci.FastDoublingMod(n, m)
	duration := time.Since(start)

	if err != nil {
		fmt.Fprintf(out, "Error: %v\n", err)
		return apperrors.ExitErrorGeneric
	}

	// Format with leading zeros to always show K digits
	formatStr := fmt.Sprintf("%%0%ds", k)
	digits := fmt.Sprintf(formatStr, result.String())

	if a.Config.Quiet {
		fmt.Fprintf(out, "...%s\n", digits)
	} else {
		fmt.Fprintf(out, "\nLast %d digits of F(%d):\n", k, n)
		fmt.Fprintf(out, "...%s\n", digits)
		fmt.Fprintf(out, "\nComputed in %s (modular, O(%d) memory)\n", duration, k)
	}

	return apperrors.ExitSuccess
}
```

**Note:** Add the necessary imports (`time`, `math/big`, `fmt`, `fibonacci`, `apperrors`) to `app.go`.

**Step 7: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./...`
Expected: ALL PASS

**Step 8: Add fuzz test for modular Fibonacci**

Add to `internal/fibonacci/fibonacci_fuzz_test.go`:

```go
func FuzzFastDoublingMod(f *testing.F) {
	f.Add(uint64(0), int64(1000))
	f.Add(uint64(1), int64(1000))
	f.Add(uint64(100), int64(10000))
	f.Add(uint64(93), int64(1000000))

	f.Fuzz(func(t *testing.T, n uint64, modVal int64) {
		if modVal <= 0 || modVal > 1_000_000_000 {
			t.Skip()
		}
		if n > 100_000 {
			t.Skip()
		}
		m := big.NewInt(modVal)
		result, err := FastDoublingMod(n, m)
		if err != nil {
			t.Fatalf("error: %v", err)
		}
		if result.Sign() < 0 || result.Cmp(m) >= 0 {
			t.Errorf("result %s out of range [0, %s)", result, m)
		}
	})
}
```

**Step 9: Commit**

```bash
git add internal/fibonacci/modular.go internal/fibonacci/modular_test.go internal/fibonacci/fibonacci_fuzz_test.go internal/config/config.go internal/app/app.go
git commit -m "$(cat <<'EOF'
feat(fibonacci): add modular fast doubling for last-K-digits mode

FastDoublingMod computes F(N) mod M in O(log N) time and O(log M) memory.
Enables computing the last K digits of F(N) for arbitrarily large N
without storing the full result. Adds --last-digits CLI flag and fuzz test.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Budget Mémoire Configurable

**Files:**
- Create: `internal/fibonacci/memory_budget.go`
- Create: `internal/fibonacci/memory_budget_test.go`
- Modify: `internal/config/config.go` (add --memory-limit flag)
- Modify: `internal/app/app.go` (pre-calculation validation)

**Step 1: Write failing test for memory estimation**

Create `internal/fibonacci/memory_budget_test.go`:

```go
package fibonacci

import (
	"fmt"
	"testing"
)

func TestEstimateMemoryUsage(t *testing.T) {
	t.Parallel()

	cases := []struct {
		n        uint64
		minBytes uint64
		maxBytes uint64
	}{
		{1_000_000, 1_000_000, 50_000_000},             // F(1M): ~1-50 Mo
		{10_000_000, 10_000_000, 500_000_000},           // F(10M): ~10-500 Mo
		{1_000_000_000, 1_000_000_000, 50_000_000_000},  // F(1B): ~1-50 Go
	}

	for _, tc := range cases {
		tc := tc
		t.Run(fmt.Sprintf("N=%d", tc.n), func(t *testing.T) {
			t.Parallel()
			est := EstimateMemoryUsage(tc.n)
			if est.TotalBytes < tc.minBytes {
				t.Errorf("estimate %d too low, want >= %d", est.TotalBytes, tc.minBytes)
			}
			if est.TotalBytes > tc.maxBytes {
				t.Errorf("estimate %d too high, want <= %d", est.TotalBytes, tc.maxBytes)
			}
		})
	}
}

func TestParseMemoryLimit(t *testing.T) {
	t.Parallel()

	cases := []struct {
		input string
		want  uint64
	}{
		{"8G", 8 * 1024 * 1024 * 1024},
		{"512M", 512 * 1024 * 1024},
		{"1024K", 1024 * 1024},
		{"1073741824", 1073741824},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.input, func(t *testing.T) {
			t.Parallel()
			got, err := ParseMemoryLimit(tc.input)
			if err != nil {
				t.Fatalf("ParseMemoryLimit(%q) error: %v", tc.input, err)
			}
			if got != tc.want {
				t.Errorf("ParseMemoryLimit(%q) = %d, want %d", tc.input, got, tc.want)
			}
		})
	}
}

func TestParseMemoryLimit_Errors(t *testing.T) {
	t.Parallel()

	cases := []string{"", "abc", "-5G", "0x10M"}
	for _, input := range cases {
		input := input
		t.Run(input, func(t *testing.T) {
			t.Parallel()
			_, err := ParseMemoryLimit(input)
			if err == nil {
				t.Errorf("ParseMemoryLimit(%q) should return error", input)
			}
		})
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `go test -v -run "TestEstimateMemoryUsage|TestParseMemoryLimit" ./internal/fibonacci/`
Expected: FAIL — `EstimateMemoryUsage` undefined

**Step 3: Implement MemoryBudget**

Create `internal/fibonacci/memory_budget.go`:

```go
package fibonacci

import (
	"fmt"
	"strconv"
	"strings"
)

// MemoryEstimate holds the estimated memory usage for a calculation.
type MemoryEstimate struct {
	StateBytes     uint64 // big.Int state (5 temporaries)
	FFTBufferBytes uint64 // bump allocator + FFT buffers
	CacheBytes     uint64 // transform cache
	OverheadBytes  uint64 // GC + runtime overhead
	TotalBytes     uint64
}

// EstimateMemoryUsage estimates the memory needed to compute F(n).
func EstimateMemoryUsage(n uint64) MemoryEstimate {
	bitsPerFib := float64(n) * 0.69424
	wordsPerFib := int(bitsPerFib/64) + 1
	bytesPerFib := uint64(wordsPerFib) * 8

	stateBytes := bytesPerFib * 5   // 5 big.Int in CalculationState
	fftBytes := bytesPerFib * 3     // bump allocator estimate
	cacheBytes := bytesPerFib * 2   // transform cache estimate
	overheadBytes := stateBytes     // GC + runtime ~1x

	total := stateBytes + fftBytes + cacheBytes + overheadBytes
	return MemoryEstimate{
		StateBytes:     stateBytes,
		FFTBufferBytes: fftBytes,
		CacheBytes:     cacheBytes,
		OverheadBytes:  overheadBytes,
		TotalBytes:     total,
	}
}

// ParseMemoryLimit parses a human-readable memory limit (e.g., "8G", "512M").
func ParseMemoryLimit(s string) (uint64, error) {
	s = strings.TrimSpace(s)
	if len(s) == 0 {
		return 0, fmt.Errorf("empty memory limit")
	}

	multiplier := uint64(1)
	suffix := s[len(s)-1]
	switch suffix {
	case 'K', 'k':
		multiplier = 1024
		s = s[:len(s)-1]
	case 'M', 'm':
		multiplier = 1024 * 1024
		s = s[:len(s)-1]
	case 'G', 'g':
		multiplier = 1024 * 1024 * 1024
		s = s[:len(s)-1]
	}

	val, err := strconv.ParseUint(s, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("invalid memory limit %q: %w", s, err)
	}

	return val * multiplier, nil
}

// FormatMemoryEstimate returns a human-readable string of the estimate.
func FormatMemoryEstimate(est MemoryEstimate) string {
	return fmt.Sprintf("State: %s, FFT: %s, Cache: %s, Overhead: %s, Total: %s",
		formatBytesInternal(est.StateBytes),
		formatBytesInternal(est.FFTBufferBytes),
		formatBytesInternal(est.CacheBytes),
		formatBytesInternal(est.OverheadBytes),
		formatBytesInternal(est.TotalBytes))
}

func formatBytesInternal(b uint64) string {
	switch {
	case b >= 1024*1024*1024:
		return fmt.Sprintf("%.1f Go", float64(b)/(1024*1024*1024))
	case b >= 1024*1024:
		return fmt.Sprintf("%.1f Mo", float64(b)/(1024*1024))
	case b >= 1024:
		return fmt.Sprintf("%.1f Ko", float64(b)/1024)
	default:
		return fmt.Sprintf("%d B", b)
	}
}
```

**Step 4: Run tests**

Run: `go test -v -run "TestEstimateMemoryUsage|TestParseMemoryLimit" ./internal/fibonacci/`
Expected: ALL PASS

**Step 5: Add --memory-limit flag to config**

In `internal/config/config.go`, add to `AppConfig`:

```go
// MemoryLimit is the maximum memory budget for calculation (e.g., "8G").
// If the estimate exceeds this limit, the application warns and exits.
MemoryLimit string
```

Add flag:

```go
fs.StringVar(&config.MemoryLimit, "memory-limit", "", "Maximum memory budget (e.g., 8G, 512M). Warns if estimate exceeds limit.")
```

**Step 6: Add pre-calculation validation in app.go**

In `internal/app/app.go`, at the top of `runCalculate` (after the `--last-digits` check):

```go
// Memory budget validation
if a.Config.MemoryLimit != "" {
	limit, err := fibonacci.ParseMemoryLimit(a.Config.MemoryLimit)
	if err != nil {
		fmt.Fprintf(out, "Invalid --memory-limit: %v\n", err)
		return apperrors.ExitErrorConfig
	}
	est := fibonacci.EstimateMemoryUsage(a.Config.N)
	if est.TotalBytes > limit {
		fmt.Fprintf(out, "Estimated memory %s exceeds limit %s.\n",
			fibonacci.FormatMemoryEstimate(est),
			a.Config.MemoryLimit)
		if a.Config.LastDigits == 0 {
			fmt.Fprintf(out, "Consider using --last-digits K for O(K) memory usage.\n")
		}
		return apperrors.ExitErrorConfig
	}
	if !a.Config.Quiet {
		fmt.Fprintf(out, "Memory estimate: %s (limit: %s)\n",
			fibonacci.FormatMemoryEstimate(est), a.Config.MemoryLimit)
	}
}
```

**Note:** Dynamic budget adaptation (reducing cache, disabling parallelism at runtime when budget is tight) is deferred to a future iteration per the PRD's "Should" priority.

**Step 7: Verify compilation and run full test suite**

Run: `go build ./... && go test -v -race -cover ./...`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add internal/fibonacci/memory_budget.go internal/fibonacci/memory_budget_test.go internal/config/config.go internal/app/app.go
git commit -m "$(cat <<'EOF'
feat(fibonacci): add memory budget estimation and --memory-limit flag

Estimates peak memory usage before calculation starts. With --memory-limit,
warns and exits if the estimate exceeds the budget, suggesting --last-digits
as an alternative. Supports human-readable sizes (8G, 512M, etc.).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Final Validation

### Task 9: Integration Test and Benchmark Suite

**Files:**
- Test: Run full test suite
- Benchmark: Compare before/after metrics

**Step 1: Run complete test suite with race detector**

Run: `go test -v -race -cover ./...`
Expected: ALL PASS, coverage >= 75% on new files

**Step 2: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 3: Run fuzz tests (short)**

Run: `go test -fuzz=FuzzFastDoublingConsistency -fuzztime=30s ./internal/fibonacci/`
Run: `go test -fuzz=FuzzFastDoublingMod -fuzztime=30s ./internal/fibonacci/`
Expected: No failures

**Step 4: Run benchmarks and compare**

Run: `go test -bench=. -benchmem -count=5 ./internal/fibonacci/ > benchmarks_after.txt`
Expected: Fewer allocs/op than baseline

**Step 5: Run linter**

Run: `golangci-lint run ./...`
Expected: No new warnings

**Step 6: Build binary**

Run: `go build ./cmd/fibcalc`
Expected: Builds successfully

**Step 7: Manual smoke tests**

Run: `./fibcalc -n 1000000 --algo fast -d`
Run: `./fibcalc -n 10000000 --last-digits 100`
Run: `./fibcalc -n 1000000 --gc-control aggressive -d`
Expected: All complete without errors

**Step 8: Verify --memory-limit**

Run: `./fibcalc -n 10000000000 --memory-limit 1G`
Expected: Should warn that estimate exceeds limit and suggest --last-digits

**Step 9: Final commit**

```bash
git commit --allow-empty -m "$(cat <<'EOF'
chore: complete Phase 1-3 memory optimization

Implemented:
- CalculationState reduced from 6 to 5 big.Int (-17% state memory)
  via algebraic reformulation F(2k) = 2·FK·FK1 - FK²
- Improved buffer pre-sizing (threshold 10K→1K, all fields, 0.69424)
- In-place multiply/square guarantees (nil-check before FFT path)
- CalculationArena for contiguous allocation (bump-pointer + fallback)
- GC controller (auto/aggressive/disabled modes)
- Memory monitoring (TUI + CLI)
- Modular fast doubling (--last-digits for O(K) memory)
- Memory budget estimation (--memory-limit)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Appendix: Deferred Items

These items from the PRD are explicitly deferred:

| PRD Feature | Status | Reason |
|---|---|---|
| F7.2 `--first-digits K` (Binet) | Deferred | Requires `big.Float` precision analysis; independent feature |
| F4.3 matrixState pre-sizing (23 big.Int) | Deferred | Matrix calculator is not the performance-critical path |
| F4.2 `bigfft.EnsureBumpCapacity()` enhancement | Deferred | Existing bump allocator already handles this adequately |
| F8.4-F8.5 Dynamic budget adaptation | Deferred | Runtime adaptation adds complexity; static pre-check is sufficient for V1 |
| F6.2 FK/FK1 size display in TUI | Deferred | Requires threading state info through observer pattern; low priority |
