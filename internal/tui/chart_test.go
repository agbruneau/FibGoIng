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

	if chart.averageProgress != 0.75 {
		t.Errorf("expected average 0.75, got %f", chart.averageProgress)
	}
}

func TestChartModel_Reset(t *testing.T) {
	chart := NewChartModel()
	chart.AddDataPoint(0.5, 0.5, 10*time.Second)
	chart.AddDataPoint(0.8, 0.8, 5*time.Second)

	chart.Reset()

	if chart.averageProgress != 0 {
		t.Errorf("expected 0 average after reset, got %f", chart.averageProgress)
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
	if !strings.Contains(view, "ETA:") {
		t.Error("expected view to contain ETA")
	}
}

func TestChartModel_RenderProgressBar(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)
	chart.AddDataPoint(0.5, 0.5, 10*time.Second)

	bar := chart.renderProgressBar()
	if !strings.Contains(bar, "█") {
		t.Error("expected progress bar to contain filled block character")
	}
	if !strings.Contains(bar, "░") {
		t.Error("expected progress bar to contain empty block character")
	}
	if !strings.Contains(bar, "50.0%") {
		t.Error("expected progress bar to show 50.0%")
	}
}

func TestChartModel_RenderProgressBar_Zero(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)
	chart.AddDataPoint(0.0, 0.0, 0)

	bar := chart.renderProgressBar()
	if !strings.Contains(bar, "░") {
		t.Error("expected progress bar to contain empty blocks at 0%")
	}
	if !strings.Contains(bar, "0.0%") {
		t.Error("expected progress bar to show 0.0%")
	}
}

func TestChartModel_RenderProgressBar_Full(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 10)
	chart.AddDataPoint(1.0, 1.0, 0)

	bar := chart.renderProgressBar()
	if !strings.Contains(bar, "█") {
		t.Error("expected progress bar to contain filled blocks at 100%")
	}
	if !strings.Contains(bar, "100.0%") {
		t.Error("expected progress bar to show 100.0%")
	}
}

func TestChartModel_RenderProgressBar_TooNarrow(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(10, 5) // too narrow for a progress bar

	bar := chart.renderProgressBar()
	if bar != "" {
		t.Error("expected empty progress bar for very narrow chart")
	}
}

func TestChartModel_View_ContainsProgressBar(t *testing.T) {
	chart := NewChartModel()
	chart.SetSize(50, 15)
	chart.AddDataPoint(0.65, 0.65, 5*time.Second)

	view := chart.View()
	if !strings.Contains(view, "█") {
		t.Error("expected view to contain progress bar filled character")
	}
	if !strings.Contains(view, "65.0%") {
		t.Error("expected view to contain progress percentage")
	}
}
