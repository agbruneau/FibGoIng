package tui

import (
	"fmt"
	"strconv"
	"strings"
	"time"
	"unicode"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/agbru/fibcalc/internal/fibonacci"
)

// updateInput handles key messages for the input section.
func (m DashboardModel) updateInput(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if !m.input.inputActive {
		return m, nil
	}

	switch {
	case key.Matches(msg, m.keys.Enter):
		return m.startSingleCalculation()
	case key.Matches(msg, m.keys.Up), key.Matches(msg, m.keys.Down):
		// Navigate to algorithms section
		m.focusedSection = SectionAlgorithms
		m.input.inputActive = false
		return m, nil
	}

	// Handle text input
	switch msg.Type {
	case tea.KeyBackspace:
		if len(m.input.n) > 0 && m.input.cursorPos > 0 {
			m.input.n = m.input.n[:m.input.cursorPos-1] + m.input.n[m.input.cursorPos:]
			m.input.cursorPos--
		}
	case tea.KeyDelete:
		if m.input.cursorPos < len(m.input.n) {
			m.input.n = m.input.n[:m.input.cursorPos] + m.input.n[m.input.cursorPos+1:]
		}
	case tea.KeyLeft:
		if m.input.cursorPos > 0 {
			m.input.cursorPos--
		}
	case tea.KeyRight:
		if m.input.cursorPos < len(m.input.n) {
			m.input.cursorPos++
		}
	case tea.KeyHome:
		m.input.cursorPos = 0
	case tea.KeyEnd:
		m.input.cursorPos = len(m.input.n)
	case tea.KeyRunes:
		// Only accept digits
		for _, r := range msg.Runes {
			if unicode.IsDigit(r) {
				m.input.n = m.input.n[:m.input.cursorPos] + string(r) + m.input.n[m.input.cursorPos:]
				m.input.cursorPos++
			}
		}
	}

	return m, nil
}

// startSingleCalculation starts a calculation with the selected algorithm.
func (m DashboardModel) startSingleCalculation() (tea.Model, tea.Cmd) {
	// Parse N
	n, err := strconv.ParseUint(m.input.n, 10, 64)
	if err != nil || n == 0 {
		m.lastError = fmt.Errorf("invalid N value: %s", m.input.n)
		return m, nil
	}

	// Get selected algorithm (use first one for single calc)
	selectedIdx := m.algorithms.cursor
	if selectedIdx >= len(m.calculators) {
		selectedIdx = 0
	}
	calc := m.calculators[selectedIdx]

	// Reset state
	m.lastError = nil
	m.calculation.active = true
	m.calculation.n = n
	m.calculation.mode = ModeSingle
	m.calculation.startTime = time.Now()
	m.calculation.progressChan = make(chan fibonacci.ProgressUpdate, 10)

	// Reset algorithm statuses
	for i := range m.algorithms.statuses {
		m.algorithms.statuses[i] = StatusIdle
		m.algorithms.progresses[i] = 0
		m.algorithms.durations[i] = 0
	}
	m.algorithms.statuses[selectedIdx] = StatusRunning

	// Focus algorithms section to show progress
	m.focusedSection = SectionAlgorithms
	m.input.inputActive = false

	// Start calculation - use config's ToCalculationOptions method
	opts := m.config.ToCalculationOptions()

	return m, tea.Batch(
		runCalculation(m.ctx, calc, n, opts, m.calculation.progressChan, selectedIdx),
		listenForProgress(m.calculation.progressChan),
	)
}

// startComparison starts a comparison of all algorithms.
func (m DashboardModel) startComparison() (tea.Model, tea.Cmd) {
	// Parse N
	n, err := strconv.ParseUint(m.input.n, 10, 64)
	if err != nil || n == 0 {
		m.lastError = fmt.Errorf("invalid N value: %s", m.input.n)
		return m, nil
	}

	// Reset state
	m.lastError = nil
	m.calculation.active = true
	m.calculation.n = n
	m.calculation.mode = ModeCompare
	m.calculation.startTime = time.Now()
	m.calculation.progressChan = make(chan fibonacci.ProgressUpdate, len(m.calculators)*10)

	// Reset algorithm statuses
	for i := range m.algorithms.statuses {
		m.algorithms.statuses[i] = StatusRunning
		m.algorithms.progresses[i] = 0
		m.algorithms.durations[i] = 0
	}

	// Focus algorithms section to show progress
	m.focusedSection = SectionAlgorithms
	m.input.inputActive = false

	// Update config with current N
	cfg := m.config
	cfg.N = n

	return m, tea.Batch(
		runComparison(m.ctx, m.calculators, cfg, m.calculation.progressChan),
		listenForProgress(m.calculation.progressChan),
	)
}

// renderInputSection renders the input section of the dashboard.
func (m DashboardModel) renderInputSection() string {
	var b strings.Builder

	// Section title
	titleStyle := m.styles.BoxTitle
	if m.focusedSection == SectionInput {
		titleStyle = titleStyle.Foreground(m.styles.Primary.GetForeground())
	}
	b.WriteString(titleStyle.Render("INPUT"))
	b.WriteString("\n\n")

	// Input field
	inputStyle := m.styles.Input
	if m.focusedSection == SectionInput && m.input.inputActive {
		inputStyle = m.styles.InputFocused
	}

	// Build input display with cursor
	display := m.input.n
	if m.focusedSection == SectionInput && m.input.inputActive {
		// Insert cursor
		if m.input.cursorPos >= len(display) {
			display = display + "█"
		} else {
			display = display[:m.input.cursorPos] + "█" + display[m.input.cursorPos:]
		}
	}
	if display == "" {
		display = "Enter N..."
	}

	inputField := fmt.Sprintf("  N: %s", inputStyle.Width(30).Render(display))

	// Buttons
	calcBtnStyle := m.styles.Button
	compareBtnStyle := m.styles.Button
	if m.focusedSection == SectionInput {
		calcBtnStyle = m.styles.ButtonFocused
	}

	calcBtn := calcBtnStyle.Render("[c] CALCULATE")
	compareBtn := compareBtnStyle.Render("[m] COMPARE ALL")

	// Status indicator
	status := ""
	if m.calculation.active {
		elapsed := time.Since(m.calculation.startTime).Round(time.Millisecond)
		status = m.styles.Info.Render(fmt.Sprintf("  Running... %v", elapsed))
	}

	b.WriteString(lipgloss.JoinHorizontal(lipgloss.Center,
		inputField,
		"  ",
		calcBtn,
		"  ",
		compareBtn,
		status,
	))

	return b.String()
}
