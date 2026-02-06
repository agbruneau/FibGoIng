// Package fibonacci provides implementations for calculating Fibonacci numbers.
// It exposes a `Calculator` interface that abstracts the underlying calculation
// algorithm, allowing different strategies (Fast Doubling, Matrix Exponentiation,
// FFT-based) to be used interchangeably. The package integrates optimizations such
// as memory pooling, parallel processing, and dynamic threshold adjustment.
package fibonacci
