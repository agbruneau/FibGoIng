package tui

import (
	"strings"
	"testing"
	"time"
)

func TestMetricsModel_UpdateMemStats(t *testing.T) {
	m := NewMetricsModel()

	msg := MemStatsMsg{
		Alloc:        1024 * 1024 * 50, // 50 MB
		HeapInuse:    1024 * 1024 * 80,
		NumGC:        10,
		NumGoroutine: 8,
	}
	m.UpdateMemStats(msg)

	if m.alloc != msg.Alloc {
		t.Errorf("expected alloc %d, got %d", msg.Alloc, m.alloc)
	}
	if m.heapInuse != msg.HeapInuse {
		t.Errorf("expected heapInuse %d, got %d", msg.HeapInuse, m.heapInuse)
	}
	if m.numGC != msg.NumGC {
		t.Errorf("expected numGC %d, got %d", msg.NumGC, m.numGC)
	}
	if m.numGoroutine != msg.NumGoroutine {
		t.Errorf("expected numGoroutine %d, got %d", msg.NumGoroutine, m.numGoroutine)
	}
}

func TestMetricsModel_UpdateProgress(t *testing.T) {
	m := NewMetricsModel()
	// Force the lastUpdate back in time to ensure dt > 0.05
	m.lastUpdate = time.Now().Add(-1 * time.Second)

	m.UpdateProgress(0.5)
	if m.speed <= 0 {
		t.Error("expected positive speed after progress update")
	}
	if m.lastProgress != 0.5 {
		t.Errorf("expected lastProgress 0.5, got %f", m.lastProgress)
	}
}

func TestMetricsModel_UpdateProgress_Smoothing(t *testing.T) {
	m := NewMetricsModel()
	m.lastUpdate = time.Now().Add(-1 * time.Second)

	// First update: dp=0.3 over ~1s → speed ≈ 0.3
	m.UpdateProgress(0.3)
	firstSpeed := m.speed

	if firstSpeed <= 0 {
		t.Fatal("precondition: first speed should be positive")
	}

	// Second update: dp=0.5 over ~0.5s → instant speed ≈ 1.0
	// Smoothed: 0.7*0.3 + 0.3*1.0 = 0.51 ≠ 0.3
	m.lastUpdate = time.Now().Add(-500 * time.Millisecond)
	m.UpdateProgress(0.8)

	if m.speed <= 0 {
		t.Error("expected positive speed after second update")
	}
	if m.speed == firstSpeed {
		t.Error("expected speed to change after second update with different rate")
	}
}

func TestMetricsModel_UpdateProgress_TooFast(t *testing.T) {
	m := NewMetricsModel()
	// lastUpdate is now, so dt < 0.05 — should not update speed
	m.UpdateProgress(0.5)

	if m.speed != 0 {
		t.Errorf("expected speed to remain 0 when dt < 0.05, got %f", m.speed)
	}
}

func TestMetricsModel_UpdateProgress_NoForward(t *testing.T) {
	m := NewMetricsModel()
	m.lastUpdate = time.Now().Add(-1 * time.Second)
	m.lastProgress = 0.5

	// Same progress (dp = 0) should not update speed
	m.UpdateProgress(0.5)

	if m.speed != 0 {
		t.Errorf("expected speed to remain 0 when no forward progress, got %f", m.speed)
	}
}

func TestMetricsModel_View(t *testing.T) {
	m := NewMetricsModel()
	m.SetSize(40, 15)

	m.UpdateMemStats(MemStatsMsg{
		Alloc:        1024 * 1024 * 50,
		HeapInuse:    1024 * 1024 * 80,
		NumGC:        10,
		NumGoroutine: 8,
	})

	view := m.View()
	if !strings.Contains(view, "Metrics") {
		t.Error("expected view to contain 'Metrics' header")
	}
	if !strings.Contains(view, "Memory") {
		t.Error("expected view to contain 'Memory' label")
	}
	if !strings.Contains(view, "Heap") {
		t.Error("expected view to contain 'Heap' label")
	}
	if !strings.Contains(view, "GC Runs") {
		t.Error("expected view to contain 'GC Runs' label")
	}
	if !strings.Contains(view, "Speed") {
		t.Error("expected view to contain 'Speed' label")
	}
	if !strings.Contains(view, "Goroutines") {
		t.Error("expected view to contain 'Goroutines' label")
	}
}

func TestFormatBytes(t *testing.T) {
	tests := []struct {
		name     string
		input    uint64
		contains string
	}{
		{"bytes", 512, "512 B"},
		{"kilobytes", 1024 * 5, "5.0 KB"},
		{"megabytes", 1024 * 1024 * 50, "50.0 MB"},
		{"gigabytes", 1024 * 1024 * 1024 * 2, "2.0 GB"},
		{"zero", 0, "0 B"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := formatBytes(tt.input)
			if !strings.Contains(got, tt.contains) {
				t.Errorf("formatBytes(%d) = %q, want to contain %q", tt.input, got, tt.contains)
			}
		})
	}
}

func TestFormatMetricLine(t *testing.T) {
	line := formatMetricLine("Memory", "50.0 MB")
	if !strings.Contains(line, "Memory") {
		t.Error("expected line to contain label")
	}
	if !strings.Contains(line, "50.0 MB") {
		t.Error("expected line to contain value")
	}
}
