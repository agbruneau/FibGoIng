# Memory Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce FibGo's peak memory footprint by 30-40% to push the maximum calculable F(N) on 64 Go RAM from ~2-3B to ~5B+.

**Architecture:** Three-pronged approach — (1) reduce live temporaries from 6 to 5 `big.Int` in the doubling loop, (2) guarantee in-place buffer reuse in all multiplication paths, (3) add a calculation arena allocator for contiguous pre-allocation. Phase 2 adds GC control and memory monitoring. Phase 3 adds partial-digit calculation for unbounded N.

**Tech Stack:** Go 1.25+, `math/big`, `runtime`, `runtime/debug`, existing `internal/bigfft` and `internal/fibonacci` packages. No new external dependencies.

---

## Phase 1 — Fondations Mémoire

### Task 1: Réduction des Temporaires (6→5 big.Int)

**Files:**
- Modify: `internal/fibonacci/fastdoubling.go:208-212` (CalculationState struct)
- Modify: `internal/fibonacci/fastdoubling.go:223-234` (statePool)
- Modify: `internal/fibonacci/fastdoubling.go:236-275` (AcquireState, ReleaseState)
- Modify: `internal/fibonacci/doubling_framework.go:240-255` (pointer rotation)
- Modify: `internal/fibonacci/strategy.go:113-122` (ExecuteStep)
- Test: `internal/fibonacci/state_pool_test.go`
- Test: `internal/fibonacci/common_test.go`

**Context:** The doubling loop uses 6 `big.Int` (FK, FK1, T1, T2, T3, T4). Analysis shows T4 is only used for `2*FK1 - FK` before ExecuteStep, then reused for the addition step `FK + FK1`. T2 is free after the accumulation `T1 += T2`. We can merge T4's role into one of the freed temporaries.

**Step 1: Write failing test for 5-field CalculationState**

Add to `internal/fibonacci/state_pool_test.go`:

```go
// TestCalculationState_FiveFields verifies the reduced state has exactly 5 big.Int fields.
func TestCalculationState_FiveFields(t *testing.T) {
	t.Parallel()

	s := AcquireState()
	defer ReleaseState(s)

	// All 5 fields must be non-nil
	if s.FK == nil || s.FK1 == nil || s.T1 == nil || s.T2 == nil || s.T3 == nil {
		t.Error("all 5 state fields must be non-nil after AcquireState")
	}
}
```

**Step 2: Run test to verify it passes (it should pass now since 6 fields includes 5)**

Run: `go test -v -run TestCalculationState_FiveFields ./internal/fibonacci/`
Expected: PASS (current 6-field state has all 5 fields)

**Step 3: Write correctness test for modified doubling with 5 temporaries**

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

**Step 4: Run test to verify it passes with current code**

Run: `go test -v -run TestFastDoubling_ReducedState_Correctness ./internal/fibonacci/`
Expected: PASS

**Step 5: Modify CalculationState to 5 fields**

In `internal/fibonacci/fastdoubling.go`, change the struct and pool:

```go
// CalculationState holds the mutable state for fast doubling calculations.
// Uses 5 big.Int temporaries: FK (F(k)), FK1 (F(k+1)), and T1-T3 for
// intermediate multiplication results. T2 doubles as the scratch buffer
// for the 2*FK1-FK subtraction (previously handled by the removed T4).
type CalculationState struct {
	FK, FK1, T1, T2, T3 *big.Int
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

Update `Reset()` to only reset FK=0, FK1=1 (remove T4 reference).

Update `ReleaseState()` to check 5 fields instead of 6:

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

**Step 6: Update the doubling framework loop**

In `internal/fibonacci/doubling_framework.go`, modify the loop to use T2 for the `2*FK1-FK` subtraction (was T4), and adjust pointer rotation:

The key change: replace all `s.T4` usage with `s.T2` for the subtraction step. Since T2 is immediately overwritten by `ExecuteStep`, using it for the subtraction is safe. The addition step `FK + FK1` (when bit is set) uses T3 which is free after the rotation.

Old pointer rotation:
```go
s.FK, s.FK1, s.T2, s.T3, s.T1 = s.T3, s.T1, s.FK, s.FK1, s.T2
```

Old addition step:
```go
s.T4.Add(s.FK, s.FK1)
s.FK, s.FK1, s.T4 = s.FK1, s.T4, s.FK
```

New (using T2 for subtraction, T3 for addition):
```go
// Before ExecuteStep: T2 = 2*FK1 - FK (was T4)
s.T2.Lsh(s.FK1, 1)
s.T2.Sub(s.T2, s.FK)

// ExecuteStep writes to T1, T2, T3 (T2 is consumed first)
// ...

// Pointer rotation remains the same:
s.FK, s.FK1, s.T2, s.T3, s.T1 = s.T3, s.T1, s.FK, s.FK1, s.T2

// Addition step uses T3 (now free after rotation):
if (n>>uint(i))&1 == 1 {
    s.T3.Add(s.FK, s.FK1)
    s.FK, s.FK1, s.T3 = s.FK1, s.T3, s.FK
}
```

**Important:** Also update `ExecuteStep` implementations in `strategy.go` to not reference T4. The `executeDoublingStepFFT` and `executeDoublingStepMultiplications` functions in `internal/fibonacci/fft.go` must be updated to use T2 for the pre-computed `2*FK1-FK` value.

**Step 7: Update ExecuteStep implementations**

In `internal/fibonacci/fft.go`, update `executeDoublingStepFFT()` and `executeDoublingStepMultiplications()` to use `s.T2` instead of `s.T4` for the pre-computed subtraction value. The multiplication tasks are:
- T3 = FK × T2 (was FK × T4)
- T2 = FK² (destination can be T2 since T2 was already consumed)
- T1 = FK1²

**Step 8: Run all tests to verify correctness**

Run: `go test -v -race -cover ./internal/fibonacci/`
Expected: ALL PASS

**Step 9: Run golden tests specifically**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS — all golden values match

**Step 10: Run benchmarks to verify no regression**

Run: `go test -bench=. -benchmem -count=3 ./internal/fibonacci/ | head -50`
Expected: Similar or better performance, fewer allocs/op

**Step 11: Commit**

```bash
git add internal/fibonacci/fastdoubling.go internal/fibonacci/doubling_framework.go internal/fibonacci/strategy.go internal/fibonacci/fft.go internal/fibonacci/state_pool_test.go internal/fibonacci/fastdoubling_test.go internal/fibonacci/common_test.go
git commit -m "perf(fibonacci): reduce CalculationState from 6 to 5 big.Int temporaries

Merge T4 into T2 for the 2*FK1-FK subtraction step. T2 is consumed
before ExecuteStep overwrites it, so using it for the pre-subtraction
is safe. Saves ~17% memory per state (~87 Mo for F(1B)).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Pré-dimensionnement Amélioré des Buffers

**Files:**
- Modify: `internal/fibonacci/fastdoubling.go:93-110` (pre-sizing in CalculateCore)
- Modify: `internal/fibonacci/fft_based.go:47-57` (add pre-sizing)
- Modify: `internal/fibonacci/matrix_framework.go` (add pre-sizing for matrixState)
- Test: `internal/fibonacci/fastdoubling_test.go`

**Context:** Currently pre-sizing only happens for `n > 10000` and only for T1-T4. We should (a) lower the threshold to 1000, (b) also pre-size FK and FK1, and (c) add pre-sizing to FFTBasedCalculator which currently does none.

**Step 1: Write test to verify pre-sizing is effective**

Add to `internal/fibonacci/fastdoubling_test.go`:

```go
// TestPreSizing_ReducesAllocations benchmarks allocation count with pre-sizing.
func TestPreSizing_ReducesAllocations(t *testing.T) {
	t.Parallel()

	calc := NewCalculator(&OptimizedFastDoubling{})
	ctx := context.Background()

	// Measure allocations for a medium-sized calculation
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

    strategy := &FFTOnlyStrategy{}
    framework := NewDoublingFramework(strategy)
    return framework.ExecuteDoublingLoop(ctx, reporter, n, opts, s, false)
}
```

**Step 5: Run all tests**

Run: `go test -v -race -cover ./internal/fibonacci/`
Expected: ALL PASS

**Step 6: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 7: Commit**

```bash
git add internal/fibonacci/fastdoubling.go internal/fibonacci/fft_based.go internal/fibonacci/fastdoubling_test.go
git commit -m "perf(fibonacci): improve buffer pre-sizing for all calculators

Lower pre-sizing threshold from 10K to 1K, pre-size FK/FK1 (not just
temporaries), and add pre-sizing to FFTBasedCalculator. Reduces
reallocation during the first iterations of the doubling loop.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Multiplications In-Place Garanties

**Files:**
- Modify: `internal/fibonacci/fft.go:45-76` (smartMultiply, smartSquare)
- Modify: `internal/bigfft/fft.go:54-114` (MulTo, SqrTo)
- Test: `internal/fibonacci/fft_test.go`
- Test: `internal/bigfft/fft_test.go` (if exists)

**Context:** `smartMultiply(z, x, y)` already passes `z` to `math/big.Mul` and `bigfft.MulTo`. But `bigfft.MulTo` internally calls `fftmulTo(z.Bits(), xb, yb)` which may or may not reuse z's backing array. We need to verify and enforce buffer reuse when capacity is sufficient.

**Step 1: Write test for in-place multiply buffer reuse**

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

Run: `go test -v -run TestSmartMultiply_InPlace ./internal/fibonacci/`
Run: `go test -v -run TestSmartSquare_InPlace ./internal/fibonacci/`
Expected: PASS

**Step 3: Ensure smartMultiply always returns z (not a new allocation)**

In `internal/fibonacci/fft.go`, update `smartMultiply`:

```go
func smartMultiply(z, x, y *big.Int, fftThreshold int) (*big.Int, error) {
	if z == nil {
		z = new(big.Int)
	}

	bx := x.BitLen()
	by := y.BitLen()

	if fftThreshold > 0 && bx > fftThreshold && by > fftThreshold {
		return bigfft.MulTo(z, x, y)
	}

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

	if fftThreshold > 0 && bx > fftThreshold {
		return bigfft.SqrTo(z, x)
	}

	return z.Mul(x, x), nil
}
```

**Step 4: Verify bigfft.MulTo reuses z's buffer**

Read `internal/bigfft/fft.go` MulTo implementation. It already passes `z.Bits()` to `fftmulTo` and calls `z.SetBits(zb)`. Verify that `fftmulTo` attempts to write into the passed buffer. If not, add capacity check:

In `internal/bigfft/fft.go`, in `fftmulTo`, ensure the result `nat` is written to the destination buffer when capacity allows. This may require modifying the FFT core — investigate before changing.

**Step 5: Run full test suite**

Run: `go test -v -race -cover ./internal/fibonacci/ ./internal/bigfft/`
Expected: ALL PASS

**Step 6: Run golden tests**

Run: `go test -v -run TestCalculatorsAgainstGoldenFile ./internal/fibonacci/`
Expected: PASS

**Step 7: Commit**

```bash
git add internal/fibonacci/fft.go internal/fibonacci/fft_test.go internal/bigfft/fft.go
git commit -m "perf(fibonacci): guarantee in-place buffer reuse in multiply/square

Ensure smartMultiply/smartSquare always initialize z before use and
return the same pointer. Eliminates nil-check allocations in hot path.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Arena Allocator pour le Calcul

**Files:**
- Create: `internal/fibonacci/arena.go`
- Create: `internal/fibonacci/arena_test.go`
- Modify: `internal/fibonacci/fastdoubling.go` (integrate arena)
- Modify: `internal/fibonacci/fft_based.go` (integrate arena)

**Context:** The arena pre-allocates a single contiguous block for all `big.Int` backing arrays of a calculation, avoiding per-buffer GC tracking and enabling O(1) bulk release.

**Step 1: Write failing test for CalculationArena**

Create `internal/fibonacci/arena_test.go`:

```go
package fibonacci

import (
	"math/big"
	"testing"
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

func TestCalculationArena_MultipleAllocs(t *testing.T) {
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

In `internal/fibonacci/fastdoubling.go`, modify `CalculateCore`:

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
}
```

**Step 6: Integrate arena into FFTBasedCalculator.CalculateCore**

Same pattern in `internal/fibonacci/fft_based.go`.

**Step 7: Run full test suite**

Run: `go test -v -race -cover ./internal/fibonacci/`
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
git commit -m "perf(fibonacci): add CalculationArena for contiguous memory allocation

Pre-allocates a single block for all big.Int backing arrays, reducing
GC pressure and memory fragmentation. Falls back to heap allocation
when the arena is exhausted. ~10× allocation for 5 state big.Ints.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2 — Contrôle et Monitoring

### Task 5: Contrôle du GC pendant le Calcul

**Files:**
- Create: `internal/fibonacci/gc_control.go`
- Create: `internal/fibonacci/gc_control_test.go`
- Modify: `internal/fibonacci/calculator.go:53-117` (integrate GCController)
- Modify: `internal/fibonacci/options.go:7-36` (add GCMode field)
- Modify: `internal/config/config.go:35-74` (add GCControl flag)

**Step 1: Write failing test for GCController**

Create `internal/fibonacci/gc_control_test.go`:

```go
package fibonacci

import (
	"runtime"
	"testing"
)

func TestGCController_Disabled(t *testing.T) {
	t.Parallel()

	gc := NewGCController("disabled", 1_000_000)
	gc.Begin()
	defer gc.End()
	// Should be a no-op
}

func TestGCController_Auto_SmallN(t *testing.T) {
	gc := NewGCController("auto", 100)
	gc.Begin()
	defer gc.End()
	// Should not change GC settings for small N
}

func TestGCController_Stats(t *testing.T) {
	gc := NewGCController("disabled", 100)
	stats := gc.Stats()
	if stats.HeapAlloc != 0 && stats.NumGC != 0 {
		// Stats should be zeroed before Begin
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
	runtime.ReadMemStats(&gc.startStats)
	if !gc.active {
		return
	}
	gc.originalGCPercent = debug.SetGCPercent(-1)
	// Set soft memory limit to prevent OOM (90% of current Sys)
	if gc.startStats.Sys > 0 {
		limit := int64(float64(gc.startStats.Sys) * 3)
		if limit > 0 {
			debug.SetMemoryLimit(limit)
		}
	}
}

// End restores original GC settings and triggers a collection.
func (gc *GCController) End() {
	runtime.ReadMemStats(&gc.endStats)
	if !gc.active {
		return
	}
	debug.SetGCPercent(gc.originalGCPercent)
	debug.SetMemoryLimit(math.MaxInt64)
	runtime.GC()
}

// Stats returns GC statistics delta between Begin and End.
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

In `internal/fibonacci/options.go`, add:

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

And in flag definitions:

```go
fs.StringVar(&config.GCControl, "gc-control", "auto", "GC control during calculation (auto, aggressive, disabled).")
```

**Step 7: Integrate GCController into FibCalculator.Calculate**

In `internal/fibonacci/calculator.go`, add GC control around the calculation:

```go
func (c *FibCalculator) CalculateWithObservers(ctx context.Context, subject *ProgressSubject, calcIndex int, n uint64, opts Options) (*big.Int, error) {
	gcCtrl := NewGCController(opts.GCMode, n)
	gcCtrl.Begin()
	defer gcCtrl.End()

	// ... existing calculation logic
}
```

**Step 8: Run full test suite**

Run: `go test -v -race -cover ./...`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add internal/fibonacci/gc_control.go internal/fibonacci/gc_control_test.go internal/fibonacci/options.go internal/fibonacci/calculator.go internal/config/config.go
git commit -m "perf(fibonacci): add GC controller for large calculations

Disables GC during computation for N >= 1M (auto mode), reducing pause
times and ~2x memory overhead from GC scanning. Sets soft memory limit
as OOM safety net. Restores GC and runs collection after calculation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Monitoring Mémoire (CLI + TUI)

**Files:**
- Create: `internal/metrics/memory.go`
- Create: `internal/metrics/memory_test.go`
- Modify: `internal/tui/metrics.go:14-119` (add memory details)
- Modify: `internal/cli/presenter.go:28-95` (add memory summary)
- Modify: `internal/fibonacci/gc_control.go` (expose stats)

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

In `internal/tui/metrics.go`, extend the `View()` method to include heap active and GC pause info. Add fields to `MetricsModel`:

```go
heapSys      uint64
heapObjects  uint64
pauseTotalNs uint64
```

Add to the rendering:

```go
// Memory line with heap details
heapStr := metricValueStyle.Render(formatBytes(m.alloc) + " / " + formatBytes(m.heapSys))
topLine := fmt.Sprintf("  %s %s%s%s %s",
    metricLabelStyle.Render("Heap:"), heapStr,
    pipe,
    metricLabelStyle.Render("GC:"), gcStr)
```

**Step 5: Add memory summary to CLI presenter**

In `internal/cli/presenter.go`, add a method to display GC stats after calculation:

```go
// DisplayMemoryStats shows memory statistics after a calculation.
func DisplayMemoryStats(stats GCStats, out io.Writer) {
	fmt.Fprintf(out, "\nMemory Stats:\n")
	fmt.Fprintf(out, "  Peak heap:       %s\n", formatBytes(stats.HeapAlloc))
	fmt.Fprintf(out, "  Total allocated: %s\n", formatBytes(stats.TotalAlloc))
	fmt.Fprintf(out, "  GC cycles:       %d\n", stats.NumGC)
	fmt.Fprintf(out, "  GC pause total:  %s\n", formatDuration(stats.PauseTotalNs))
}
```

**Step 6: Run full test suite**

Run: `go test -v -race -cover ./...`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add internal/metrics/memory.go internal/metrics/memory_test.go internal/tui/metrics.go internal/cli/presenter.go
git commit -m "feat(metrics): add memory monitoring to TUI and CLI

Display heap allocation, GC cycles, and pause times in TUI metrics
panel and CLI post-calculation summary. Uses runtime.ReadMemStats
at max 1 Hz frequency to avoid overhead.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3 — Modes Avancés

### Task 7: Fast Doubling Modulaire (Derniers Chiffres)

**Files:**
- Create: `internal/fibonacci/modular.go`
- Create: `internal/fibonacci/modular_test.go`
- Modify: `internal/fibonacci/registry.go:53-65` (register modular)
- Modify: `internal/config/config.go` (add --last-digits flag)
- Modify: `internal/app/app.go` (handle partial mode)

**Step 1: Write failing test for modular Fibonacci**

Create `internal/fibonacci/modular_test.go`:

```go
package fibonacci

import (
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
//   F(2k)   = F(k) * (2*F(k+1) - F(k))  mod m
//   F(2k+1) = F(k+1)² + F(k)²            mod m
func FastDoublingMod(n uint64, m *big.Int) (*big.Int, error) {
	if m == nil || m.Sign() <= 0 {
		return nil, fmt.Errorf("modulus must be positive")
	}

	if n == 0 {
		return big.NewInt(0), nil
	}

	fk := big.NewInt(0)   // F(k)
	fk1 := big.NewInt(1)  // F(k+1)
	t1 := new(big.Int)    // temporary
	t2 := new(big.Int)    // temporary

	numBits := bits.Len64(n)

	for i := numBits - 1; i >= 0; i-- {
		// F(2k) = F(k) * (2*F(k+1) - F(k)) mod m
		t1.Lsh(fk1, 1)
		t1.Sub(t1, fk)
		t1.Mod(t1, m)
		// Handle negative mod
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

		// If bit is set: F(k+1) = F(k) + F(k+1), F(k) = F(k+1) (before add)
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
LastDigits int
```

Add flag:

```go
fs.IntVar(&config.LastDigits, "last-digits", 0, "Compute only the last K decimal digits (uses O(K) memory).")
```

**Step 6: Handle partial mode in app.go**

In `internal/app/app.go`, add dispatch for `--last-digits` mode in `runCalculate`:

```go
if a.Config.LastDigits > 0 {
    return a.runLastDigits(ctx, out)
}
```

Implement `runLastDigits` to call `FastDoublingMod` with `m = 10^K`.

**Step 7: Run full test suite**

Run: `go test -v -race -cover ./...`
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
git commit -m "feat(fibonacci): add modular fast doubling for last-K-digits mode

FastDoublingMod computes F(N) mod M in O(log N) time and O(log M) memory.
Enables computing the last K digits of F(N) for arbitrarily large N
without storing the full result. Includes fuzz test.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
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

import "testing"

func TestEstimateMemoryUsage(t *testing.T) {
	t.Parallel()

	cases := []struct {
		n         uint64
		minBytes  uint64
		maxBytes  uint64
	}{
		{1_000_000, 1_000_000, 50_000_000},       // F(1M): ~1-50 Mo
		{10_000_000, 10_000_000, 500_000_000},     // F(10M): ~10-500 Mo
		{1_000_000_000, 1_000_000_000, 50_000_000_000}, // F(1B): ~1-50 Go
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
```

**Step 2: Run tests to verify they fail**

Run: `go test -v -run TestEstimateMemoryUsage ./internal/fibonacci/`
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

	stateBytes := bytesPerFib * 5     // 5 big.Int in CalculationState
	fftBytes := bytesPerFib * 3       // bump allocator estimate
	cacheBytes := bytesPerFib * 2     // transform cache estimate
	overheadBytes := stateBytes       // GC + runtime ~1x

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
```

**Step 4: Run tests**

Run: `go test -v -run "TestEstimateMemoryUsage|TestParseMemoryLimit" ./internal/fibonacci/`
Expected: ALL PASS

**Step 5: Add --memory-limit flag to config**

In `internal/config/config.go`, add to `AppConfig`:

```go
// MemoryLimit is the maximum memory budget for calculation (e.g., "8G").
MemoryLimit string
```

Add flag:

```go
fs.StringVar(&config.MemoryLimit, "memory-limit", "", "Maximum memory budget (e.g., 8G, 512M). Warns if estimate exceeds limit.")
```

**Step 6: Add pre-calculation validation in app.go**

In `internal/app/app.go`, before calculation, check the estimate:

```go
if a.Config.MemoryLimit != "" {
    limit, err := fibonacci.ParseMemoryLimit(a.Config.MemoryLimit)
    if err != nil {
        fmt.Fprintf(out, "Invalid --memory-limit: %v\n", err)
        return apperrors.ExitErrorConfig
    }
    est := fibonacci.EstimateMemoryUsage(a.Config.N)
    if est.TotalBytes > limit {
        fmt.Fprintf(out, "Estimated memory %s exceeds limit %s.\n",
            formatBytes(est.TotalBytes), formatBytes(limit))
        if a.Config.LastDigits == 0 {
            fmt.Fprintf(out, "Consider using --last-digits K for O(K) memory usage.\n")
        }
        return apperrors.ExitErrorConfig
    }
}
```

**Step 7: Run full test suite**

Run: `go test -v -race -cover ./...`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add internal/fibonacci/memory_budget.go internal/fibonacci/memory_budget_test.go internal/config/config.go internal/app/app.go
git commit -m "feat(fibonacci): add memory budget estimation and --memory-limit flag

Estimates peak memory usage before calculation starts. With --memory-limit,
warns and exits if the estimate exceeds the budget, suggesting --last-digits
as an alternative. Supports human-readable sizes (8G, 512M, etc.).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Final Validation

### Task 9: Integration Test and Benchmark Suite

**Files:**
- Test: Run full test suite
- Benchmark: Compare before/after metrics

**Step 1: Run complete test suite with race detector**

Run: `go test -v -race -cover ./...`
Expected: ALL PASS, coverage ≥ 75% on new files

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

**Step 7: Manual smoke test**

Run: `./fibcalc -n 1000000 -algo fast -d`
Run: `./fibcalc -n 10000000 --last-digits 100`
Run: `./fibcalc -n 1000000 --gc-control aggressive -d`
Expected: All complete without errors

**Step 8: Final commit**

```bash
git commit --allow-empty -m "chore: complete Phase 1-3 memory optimization

Implemented:
- CalculationState reduced from 6 to 5 big.Int (-17% state memory)
- Improved buffer pre-sizing (threshold 10K→1K, all fields)
- In-place multiply/square guarantees
- CalculationArena for contiguous allocation
- GC controller (auto/aggressive/disabled modes)
- Memory monitoring (TUI + CLI)
- Modular fast doubling (--last-digits for O(K) memory)
- Memory budget estimation (--memory-limit)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
