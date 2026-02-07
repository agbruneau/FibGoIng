package bigfft

import (
	"fmt"
	"math/big"
	"math/rand"
	"testing"
)

// TestFermatSqrVsMul verifies that fermat.Sqr(x) produces the same result
// as fermat.Mul(x, x) for various sizes, crossing the smallMulThreshold boundary.
func TestFermatSqrVsMul(t *testing.T) {
	t.Parallel()
	rng := rand.New(rand.NewSource(42))

	// Test sizes spanning below and above smallMulThreshold (30)
	sizes := []int{1, 2, 3, 5, 10, 15, 20, 25, 29, 30, 31, 35, 40, 50}

	for _, n := range sizes {
		n := n
		t.Run(fmt.Sprintf("n=%d", n), func(t *testing.T) {
			t.Parallel()
			// Create random fermat number of size n+1 words
			x := make(fermat, n+1)
			for j := 0; j < n; j++ {
				x[j] = big.Word(rng.Uint64())
			}
			x[n] = big.Word(rng.Intn(2)) // last word 0 or 1

			// Compute via Mul(x, x)
			bufMul := make(fermat, 8*n)
			resMul := bufMul.Mul(x, x)

			// Compute via Sqr(x)
			bufSqr := make(fermat, 8*n)
			resSqr := bufSqr.Sqr(x)

			// Compare
			if len(resMul) != len(resSqr) {
				t.Fatalf("n=%d: length mismatch: Mul=%d, Sqr=%d", n, len(resMul), len(resSqr))
			}
			for i := range resMul {
				if resMul[i] != resSqr[i] {
					t.Fatalf("n=%d: word %d mismatch: Mul=%x, Sqr=%x", n, i, resMul[i], resSqr[i])
				}
			}
		})
	}
}

// TestFermatSqrZero verifies that squaring a zero fermat number produces zero.
func TestFermatSqrZero(t *testing.T) {
	t.Parallel()
	for _, n := range []int{1, 5, 10, 30, 50} {
		n := n
		t.Run(fmt.Sprintf("n=%d", n), func(t *testing.T) {
			t.Parallel()
			x := make(fermat, n+1) // all zeros
			buf := make(fermat, 8*n)
			res := buf.Sqr(x)
			for i, w := range res {
				if w != 0 {
					t.Fatalf("n=%d: Sqr(0) non-zero at word %d: %x", n, i, w)
				}
			}
		})
	}
}

// TestFermatSqrOne verifies squaring when x = 1 (only first word is 1).
func TestFermatSqrOne(t *testing.T) {
	t.Parallel()
	for _, n := range []int{1, 5, 10, 30, 50} {
		n := n
		t.Run(fmt.Sprintf("n=%d", n), func(t *testing.T) {
			t.Parallel()
			x := make(fermat, n+1)
			x[0] = 1

			bufMul := make(fermat, 8*n)
			resMul := bufMul.Mul(x, x)

			bufSqr := make(fermat, 8*n)
			resSqr := bufSqr.Sqr(x)

			for i := range resMul {
				if resMul[i] != resSqr[i] {
					t.Fatalf("n=%d: word %d mismatch: Mul=%x, Sqr=%x", n, i, resMul[i], resSqr[i])
				}
			}
		})
	}
}

// TestFermatSqrMaxWord verifies squaring when all words are max value.
func TestFermatSqrMaxWord(t *testing.T) {
	t.Parallel()
	for _, n := range []int{1, 5, 10, 29, 30, 31} {
		n := n
		t.Run(fmt.Sprintf("n=%d", n), func(t *testing.T) {
			t.Parallel()
			x := make(fermat, n+1)
			for j := 0; j < n; j++ {
				x[j] = ^big.Word(0)
			}
			x[n] = 1

			bufMul := make(fermat, 8*n)
			resMul := bufMul.Mul(x, x)

			bufSqr := make(fermat, 8*n)
			resSqr := bufSqr.Sqr(x)

			for i := range resMul {
				if resMul[i] != resSqr[i] {
					t.Fatalf("n=%d: word %d mismatch: Mul=%x, Sqr=%x", n, i, resMul[i], resSqr[i])
				}
			}
		})
	}
}

// TestBasicSqrVsBasicMul verifies basicSqr directly against basicMul for small sizes.
func TestBasicSqrVsBasicMul(t *testing.T) {
	t.Parallel()
	rng := rand.New(rand.NewSource(123))

	for n := 1; n < smallMulThreshold; n++ {
		n := n
		t.Run(fmt.Sprintf("n=%d", n), func(t *testing.T) {
			t.Parallel()
			x := make(fermat, n)
			for j := 0; j < n; j++ {
				x[j] = big.Word(rng.Uint64())
			}

			zMul := make(fermat, 2*n)
			basicMul(zMul, x, x)

			zSqr := make(fermat, 2*n)
			basicSqr(zSqr, x)

			for i := range zMul {
				if zMul[i] != zSqr[i] {
					t.Fatalf("n=%d: word %d mismatch: basicMul=%x, basicSqr=%x", n, i, zMul[i], zSqr[i])
				}
			}
		})
	}
}

// BenchmarkFermatSqrVsMul benchmarks fermat.Sqr vs fermat.Mul at sizes
// below and above smallMulThreshold.
func BenchmarkFermatSqrVsMul(b *testing.B) {
	rng := rand.New(rand.NewSource(42))

	for _, n := range []int{10, 29, 30, 50} {
		x := make(fermat, n+1)
		for j := 0; j < n; j++ {
			x[j] = big.Word(rng.Uint64())
		}

		b.Run(fmt.Sprintf("n=%d/Mul", n), func(b *testing.B) {
			buf := make(fermat, 8*n)
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				buf.Mul(x, x)
			}
		})

		b.Run(fmt.Sprintf("n=%d/Sqr", n), func(b *testing.B) {
			buf := make(fermat, 8*n)
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				buf.Sqr(x)
			}
		})
	}
}
