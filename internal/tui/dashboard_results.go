package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
)

// updateResults handles key messages for the results section.
func (m DashboardModel) updateResults(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if !m.results.hasResults {
		return m, nil
	}

	switch {
	case key.Matches(msg, m.keys.Up):
		if m.results.cursor > 0 {
			m.results.cursor--
		}
	case key.Matches(msg, m.keys.Down):
		if m.results.cursor < len(m.results.results)-1 {
			m.results.cursor++
		}
	}
	return m, nil
}

// renderResultsSection renders the results section of the dashboard.
func (m DashboardModel) renderResultsSection() string {
	var b strings.Builder

	// Section title
	titleStyle := m.styles.BoxTitle
	if m.focusedSection == SectionResults {
		titleStyle = titleStyle.Foreground(m.styles.Primary.GetForeground())
	}
	b.WriteString(titleStyle.Render("RESULT"))
	b.WriteString("\n\n")

	if !m.results.hasResults {
		b.WriteString(m.styles.Muted.Render("  No results yet. Press [c] to calculate or [m] to compare."))
		return b.String()
	}

	// Get the best result
	var bestResult string
	var bestAlgo string
	var bestDuration string

	if len(m.results.results) > 0 {
		for _, r := range m.results.results {
			if r.Err == nil && r.Result != nil {
				if bestResult == "" {
					bestResult = r.Result.String()
					bestAlgo = r.Name
					bestDuration = formatDuration(r.Duration)
				}
				break
			}
		}
	}

	if bestResult == "" {
		b.WriteString(m.styles.Error.Render("  All calculations failed."))
		return b.String()
	}

	// Format result
	displayResult := formatResultValue(bestResult, m.results.showHex, m.results.showFull, m.getMaxValueLength())
	digitCount := len(bestResult)

	// Result line
	b.WriteString(fmt.Sprintf("  %s = %s  (%s digits)\n",
		m.styles.Primary.Render(fmt.Sprintf("F(%d)", m.results.n)),
		m.styles.ResultValue.Render(displayResult),
		m.styles.Info.Render(formatNumber(digitCount)),
	))

	// Stats line
	b.WriteString(fmt.Sprintf("  Fastest: %s (%s)",
		m.styles.Success.Render(bestAlgo),
		m.styles.Muted.Render(bestDuration),
	))

	// Consistency check
	if len(m.results.results) > 1 {
		if m.results.consistent {
			b.WriteString(m.styles.Success.Render("       ✓ All results consistent"))
		} else {
			b.WriteString(m.styles.Error.Render("       ✗ Results inconsistent!"))
		}
	}

	// Actions hint
	b.WriteString("\n\n")
	b.WriteString(m.styles.Muted.Render("  [x] Toggle hex  [v] Toggle full value  [Ctrl+S] Save"))

	return b.String()
}

// formatResultValue formats the result value for display.
func formatResultValue(result string, showHex, showFull bool, maxLen int) string {
	if showFull {
		return result
	}

	if len(result) <= maxLen {
		return result
	}

	// Truncate with ellipsis
	half := (maxLen - 3) / 2
	return result[:half] + "..." + result[len(result)-half:]
}

// formatNumber formats a number with thousand separators.
func formatNumber(n int) string {
	str := fmt.Sprintf("%d", n)
	if len(str) <= 3 {
		return str
	}

	var result strings.Builder
	remainder := len(str) % 3
	if remainder > 0 {
		result.WriteString(str[:remainder])
		if len(str) > remainder {
			result.WriteString(",")
		}
	}

	for i := remainder; i < len(str); i += 3 {
		result.WriteString(str[i : i+3])
		if i+3 < len(str) {
			result.WriteString(",")
		}
	}

	return result.String()
}

// getMaxValueLength returns the maximum result value length based on terminal width.
func (m DashboardModel) getMaxValueLength() int {
	if m.width > 160 {
		return 120
	}
	if m.width > 120 {
		return 80
	}
	if m.width > 80 {
		return 50
	}
	return 30
}
