package app

import (
	"testing"

	"github.com/agbruneau/FibGo/internal/config"
	"github.com/agbruneau/FibGo/internal/fibonacci/threshold"
)

// The two packages keep independent copies of the dynamic-threshold defaults,
// because internal/fibonacci/threshold must not import internal/config — that
// would close a cycle through fibonacci/memory. These tests are what keeps the
// copies honest.
//
// This replaces TestWireThresholdTuning, which asserted that a startup call had
// written config's values into package-level variables in the threshold package
// (audit TYP-02). There are no such variables now: the values travel by value in
// fibonacci.Options, so what is left to check is the translation and the
// agreement between the two sets of defaults.

func TestThresholdTuningFromConfig(t *testing.T) {
	t.Parallel()

	p := config.DefaultThresholdTuning
	got := thresholdTuningFromConfig()

	want := threshold.Tuning{
		FFTSpeedupThreshold:      p.FFTSpeedupThreshold,
		ParallelSpeedupThreshold: p.ParallelSpeedupThreshold,
		HysteresisMargin:         p.HysteresisMargin,
		MinFFTThreshold:          p.MinFFTThreshold,
		MinParallelThreshold:     p.MinParallelThreshold,
	}
	if got != want {
		t.Errorf("thresholdTuningFromConfig() = %+v, want %+v", got, want)
	}
}

// A drift between the two default sets would mean the binary silently tunes
// differently from what internal/config documents.
func TestThresholdTuningMatchesDefaults(t *testing.T) {
	t.Parallel()

	p := config.DefaultThresholdTuning
	d := threshold.DefaultTuning

	if d.FFTSpeedupThreshold != p.FFTSpeedupThreshold {
		t.Errorf("FFTSpeedupThreshold: threshold=%v, config=%v", d.FFTSpeedupThreshold, p.FFTSpeedupThreshold)
	}
	if d.ParallelSpeedupThreshold != p.ParallelSpeedupThreshold {
		t.Errorf("ParallelSpeedupThreshold: threshold=%v, config=%v", d.ParallelSpeedupThreshold, p.ParallelSpeedupThreshold)
	}
	if d.HysteresisMargin != p.HysteresisMargin {
		t.Errorf("HysteresisMargin: threshold=%v, config=%v", d.HysteresisMargin, p.HysteresisMargin)
	}
	if d.MinFFTThreshold != p.MinFFTThreshold {
		t.Errorf("MinFFTThreshold: threshold=%v, config=%v", d.MinFFTThreshold, p.MinFFTThreshold)
	}
	if d.MinParallelThreshold != p.MinParallelThreshold {
		t.Errorf("MinParallelThreshold: threshold=%v, config=%v", d.MinParallelThreshold, p.MinParallelThreshold)
	}
}
