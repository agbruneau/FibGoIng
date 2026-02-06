package tui

import (
	"strings"
	"testing"
	"time"
)

func TestChartModel_AddDataPoint(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)

	chart.AddDataPoint(0.25, 0.25, 30*time.Second)
	chart.AddDataPoint(0.50, 0.50, 20*time.Second)
	chart.AddDataPoint(0.75, 0.75, 10*time.Second)

	if len(chart.dataPoints) != 3 {
		t.Errorf("expected 3 data points, got %d", len(chart.dataPoints))
	}
	if chart.averageProgress != 0.75 {
		t.Errorf("expected average 0.75, got %f", chart.averageProgress)
	}
}

func TestChartModel_AddDataPoint_Overflow(t *testing.T) {
	chart := NewChartModel()
	chart.maxPoints = 5

	for i := 0; i < 10; i++ {
		chart.AddDataPoint(float64(i)/10.0, float64(i)/10.0, 0)
	}

	if len(chart.dataPoints) != 5 {
		t.Errorf("expected 5 data points (capped), got %d", len(chart.dataPoints))
	}
}

func TestChartModel_Reset(t *testing.T) {
	chart := NewChartModel()
	chart.AddDataPoint(0.5, 0.5, 10*time.Second)
	chart.AddDataPoint(0.8, 0.8, 5*time.Second)

	chart.Reset()

	if len(chart.dataPoints) != 0 {
		t.Errorf("expected 0 data points after reset, got %d", len(chart.dataPoints))
	}
	if chart.averageProgress != 0 {
		t.Errorf("expected 0 average after reset, got %f", chart.averageProgress)
	}
}

func TestChartModel_RenderSparkline(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)

	// Empty sparkline
	if s := chart.renderSparkline(); s != "" {
		t.Errorf("expected empty sparkline for no data, got %q", s)
	}

	// Add data points
	chart.AddDataPoint(0.0, 0.0, 0)
	chart.AddDataPoint(0.5, 0.5, 0)
	chart.AddDataPoint(1.0, 1.0, 0)

	sparkline := chart.renderSparkline()
	if len(sparkline) == 0 {
		t.Error("expected non-empty sparkline")
	}

	// Should contain block characters
	for _, r := range sparkline {
		found := false
		for _, block := range sparkBlocks {
			if r == block {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("unexpected character in sparkline: %q", string(r))
		}
	}
}

func TestChartModel_View(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)

	chart.AddDataPoint(0.3, 0.3, 20*time.Second)
	chart.AddDataPoint(0.6, 0.6, 10*time.Second)

	view := chart.View()
	if !strings.Contains(view, "Progress Chart") {
		t.Error("expected view to contain 'Progress Chart'")
	}
	if !strings.Contains(view, "avg:") {
		t.Error("expected view to contain average progress")
	}
	if !strings.Contains(view, "ETA:") {
		t.Error("expected view to contain ETA")
	}
}

func TestChartModel_SetSize_TrimsData(t *testing.T) {
	chart := NewChartModel()
	chart.maxPoints = 100

	for i := 0; i < 50; i++ {
		chart.AddDataPoint(float64(i)/50.0, float64(i)/50.0, 0)
	}

	// Shrink size to force trim
	chart.SetSize(15, 10) // maxPoints will be 15-6 = 9

	if len(chart.dataPoints) > chart.maxPoints {
		t.Errorf("expected data points <= %d, got %d", chart.maxPoints, len(chart.dataPoints))
	}
}
