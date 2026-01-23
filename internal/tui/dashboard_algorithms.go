package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
)

// updateAlgorithms handles key messages for the algorithms section.
func (m DashboardModel) updateAlgorithms(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Up):
		if m.algorithms.cursor > 0 {
			m.algorithms.cursor--
		}
	case key.Matches(msg, m.keys.Down):
		if m.algorithms.cursor < len(m.algorithms.names)-1 {
			m.algorithms.cursor++
		}
	case key.Matches(msg, m.keys.Enter):
		// Start calculation with selected algorithm
		return m.startSingleCalculation()
	}
	return m, nil
}

// renderAlgorithmTable renders the algorithm comparison table.
func (m DashboardModel) renderAlgorithmTable() string {
	var b strings.Builder

	// Section title
	titleStyle := m.styles.BoxTitle
	if m.focusedSection == SectionAlgorithms {
		titleStyle = titleStyle.Foreground(m.styles.Primary.GetForeground())
	}
	b.WriteString(titleStyle.Render("ALGORITHMS"))
	b.WriteString("\n\n")

	// Table header
	header := fmt.Sprintf("  %-3s %-18s %-32s %6s  %-12s %s",
		"#", "Algorithm", "Progress", "%", "Duration", "Status")
	b.WriteString(m.styles.TableHeader.Render(header))
	b.WriteString("\n")

	// Separator
	b.WriteString(m.styles.Muted.Render(strings.Repeat("─", 90)))
	b.WriteString("\n")

	// Algorithm rows
	for i, name := range m.algorithms.names {
		row := m.renderAlgorithmRow(i, name)
		b.WriteString(row)
		b.WriteString("\n")
	}

	return b.String()
}

// renderAlgorithmRow renders a single algorithm row.
func (m DashboardModel) renderAlgorithmRow(idx int, name string) string {
	progress := m.algorithms.progresses[idx]
	duration := m.algorithms.durations[idx]
	status := m.algorithms.statuses[idx]

	// Row style
	rowStyle := m.styles.TableRow
	if m.focusedSection == SectionAlgorithms && idx == m.algorithms.cursor {
		rowStyle = m.styles.MenuItemActive
	}

	// Rank column
	rank := fmt.Sprintf("%d", idx+1)
	if status == StatusComplete && m.results.hasResults && len(m.results.results) > 0 {
		// Find position in results (sorted by duration)
		for pos, r := range m.results.results {
			if r.Name == name {
				rank = fmt.Sprintf("%d", pos+1)
				if pos == 0 {
					rank = m.styles.Success.Render("1")
				}
				break
			}
		}
	}

	// Progress bar
	bar := m.renderProgressBar(progress, 30)

	// Percentage
	pct := fmt.Sprintf("%5.1f%%", progress*100)

	// Duration column
	durStr := "     -     "
	if status == StatusComplete {
		durStr = fmt.Sprintf("%12s", formatDuration(duration))
	} else if status == StatusRunning && m.calculation.active {
		durStr = fmt.Sprintf("%12s", "...")
	}

	// Status indicator
	var statusStr string
	switch status {
	case StatusIdle:
		statusStr = m.styles.Muted.Render("IDLE")
	case StatusRunning:
		statusStr = m.styles.Info.Render(" ▶  ")
	case StatusComplete:
		statusStr = m.styles.Success.Render(" OK ")
	case StatusError:
		statusStr = m.styles.Error.Render("ERR ")
	}

	// Build row
	row := fmt.Sprintf("  %-3s %-18s %s %s %s %s",
		rank, name, bar, pct, durStr, statusStr)

	return rowStyle.Render(row)
}

// renderProgressBar renders a progress bar.
func (m DashboardModel) renderProgressBar(progress float64, width int) string {
	filled := int(progress * float64(width))
	if filled > width {
		filled = width
	}

	filledStr := strings.Repeat("█", filled)
	emptyStr := strings.Repeat("░", width-filled)

	return m.styles.ProgressFilled.Render(filledStr) + m.styles.ProgressEmpty.Render(emptyStr)
}

// formatDuration formats a duration for display.
func formatDuration(d time.Duration) string {
	if d < time.Microsecond {
		return fmt.Sprintf("%dns", d.Nanoseconds())
	}
	if d < time.Millisecond {
		return fmt.Sprintf("%.1fµs", float64(d.Nanoseconds())/1000)
	}
	if d < time.Second {
		return fmt.Sprintf("%.1fms", float64(d.Microseconds())/1000)
	}
	if d < time.Minute {
		return fmt.Sprintf("%.2fs", d.Seconds())
	}
	return d.Round(time.Second).String()
}
