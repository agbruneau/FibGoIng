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
func (gc *GCController) Stats() GCStats {
	return GCStats{
		HeapAlloc:    gc.endStats.HeapAlloc,
		TotalAlloc:   gc.endStats.TotalAlloc - gc.startStats.TotalAlloc,
		NumGC:        gc.endStats.NumGC - gc.startStats.NumGC,
		PauseTotalNs: gc.endStats.PauseTotalNs - gc.startStats.PauseTotalNs,
	}
}
