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
// (5 state + 5 margin for multiplications) of size ~ n * 0.69424 bits.
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
