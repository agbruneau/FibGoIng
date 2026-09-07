package threshold

import "testing"

// Tuning is per-manager, carried by value (audit TYP-02). Two managers built
// from different tunings must behave differently, and one built from the zero
// value must behave like DefaultTuning.
//
// What this replaces was a test that called SetTuning and then read package
// variables — an assertion about process state that only held as long as no
// other test wrote the same variables, which is exactly the fragility the
// "single-writer-before-use" protocol was documenting rather than fixing.
func TestTuningIsPerManagerNotGlobal(t *testing.T) {
	t.Parallel()

	base := DynamicThresholdConfig{
		InitialFFTThreshold:      500_000,
		InitialParallelThreshold: 4096,
		Enabled:                  true,
	}

	tight := base
	tight.Tuning = Tuning{HysteresisMargin: 0.0001}

	loose := base
	loose.Tuning = Tuning{HysteresisMargin: 0.9}

	zeroValue := NewDynamicThresholdManagerFromConfig(base)
	sensitive := NewDynamicThresholdManagerFromConfig(tight)
	insensitive := NewDynamicThresholdManagerFromConfig(loose)

	// A 20% move: above the default 0.15 margin, far above 0.0001, far below 0.9.
	const from, to = 100_000, 120_000

	if !zeroValue.analyzer.SignificantChange(from, to) {
		t.Error("zero-value tuning did not fall back to the default margin")
	}
	if !sensitive.analyzer.SignificantChange(from, to) {
		t.Error("a 0.0001 margin should treat a 20% move as significant")
	}
	if insensitive.analyzer.SignificantChange(from, to) {
		t.Error("a 0.9 margin should treat a 20% move as insignificant")
	}

	// The managers must not have disturbed each other: re-check after all three
	// exist, which is what a package-global knob could not survive.
	if !sensitive.analyzer.SignificantChange(from, to) {
		t.Error("the sensitive manager's margin was overwritten by a later one")
	}
}

// withDefaults fills only what the caller left unset.
func TestTuningWithDefaults(t *testing.T) {
	t.Parallel()

	if got := (Tuning{}).withDefaults(); got != DefaultTuning {
		t.Errorf("zero value = %+v, want %+v", got, DefaultTuning)
	}

	partial := Tuning{HysteresisMargin: 0.42}.withDefaults()
	if partial.HysteresisMargin != 0.42 {
		t.Errorf("HysteresisMargin = %v, want the caller's 0.42", partial.HysteresisMargin)
	}
	if partial.FFTSpeedupThreshold != DefaultTuning.FFTSpeedupThreshold {
		t.Errorf("FFTSpeedupThreshold = %v, want the default %v",
			partial.FFTSpeedupThreshold, DefaultTuning.FFTSpeedupThreshold)
	}
	if partial.MinParallelThreshold != DefaultTuning.MinParallelThreshold {
		t.Errorf("MinParallelThreshold = %v, want the default %v",
			partial.MinParallelThreshold, DefaultTuning.MinParallelThreshold)
	}

	// A negative value is treated as unset, not honored.
	if got := (Tuning{HysteresisMargin: -1}).withDefaults(); got.HysteresisMargin != DefaultTuning.HysteresisMargin {
		t.Errorf("negative margin = %v, want the default", got.HysteresisMargin)
	}
}
