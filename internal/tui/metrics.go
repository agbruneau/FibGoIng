package tui

import (
	"fmt"
	"time"

	"github.com/agbru/fibcalc/internal/cli"
)

// MetricsModel displays runtime memory and performance metrics.
type MetricsModel struct {
	alloc        uint64
	heapInuse    uint64
	numGC        uint32
	numGoroutine int
	speed        float64 // progress per second
	lastProgress float64
	lastUpdate   time.Time
	width        int
	height       int
}

// NewMetricsModel creates a new metrics panel.
func NewMetricsModel() MetricsModel {
	return MetricsModel{
		lastUpdate: time.Now(),
	}
}

// SetSize updates dimensions.
func (m *MetricsModel) SetSize(w, h int) {
	m.width = w
	m.height = h
}

// UpdateMemStats updates memory statistics.
func (m *MetricsModel) UpdateMemStats(msg MemStatsMsg) {
	m.alloc = msg.Alloc
	m.heapInuse = msg.HeapInuse
	m.numGC = msg.NumGC
	m.numGoroutine = msg.NumGoroutine
}

// UpdateProgress updates the speed metric.
func (m *MetricsModel) UpdateProgress(progress float64) {
	now := time.Now()
	dt := now.Sub(m.lastUpdate).Seconds()
	if dt > 0.05 {
		dp := progress - m.lastProgress
		if dp > 0 {
			instantSpeed := dp / dt
			if m.speed > 0 {
				m.speed = 0.7*m.speed + 0.3*instantSpeed
			} else {
				m.speed = instantSpeed
			}
		}
		m.lastProgress = progress
		m.lastUpdate = now
	}
}

// View renders the metrics panel.
func (m MetricsModel) View() string {
	lines := []string{
		metricLabelStyle.Render("  Metrics"),
		"",
		formatMetricLine("Memory", formatBytes(m.alloc)),
		formatMetricLine("Heap", formatBytes(m.heapInuse)),
		formatMetricLine("GC Runs", fmt.Sprintf("%d", m.numGC)),
		formatMetricLine("Speed", cli.FormatETA(time.Duration(float64(time.Second)/max(m.speed, 0.001)))+"/calc"),
		formatMetricLine("Goroutines", fmt.Sprintf("%d", m.numGoroutine)),
	}

	content := ""
	for i, line := range lines {
		if i > 0 {
			content += "\n"
		}
		content += line
	}

	return panelStyle.
		Width(m.width - 2).
		Height(m.height - 2).
		Render(content)
}

func formatMetricLine(label, value string) string {
	return fmt.Sprintf("   %s  %s",
		metricLabelStyle.Render(fmt.Sprintf("%-12s", label+":")),
		metricValueStyle.Render(value))
}

func formatBytes(b uint64) string {
	switch {
	case b >= 1<<30:
		return fmt.Sprintf("%.1f GB", float64(b)/(1<<30))
	case b >= 1<<20:
		return fmt.Sprintf("%.1f MB", float64(b)/(1<<20))
	case b >= 1<<10:
		return fmt.Sprintf("%.1f KB", float64(b)/(1<<10))
	default:
		return fmt.Sprintf("%d B", b)
	}
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
