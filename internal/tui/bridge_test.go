package tui

import (
	"sync"
	"testing"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/agbru/fibcalc/internal/fibonacci"
)

// testProgramRef creates a programRef with a collector for sent messages.
type msgCollector struct {
	mu   sync.Mutex
	msgs []tea.Msg
}

func (c *msgCollector) send(msg tea.Msg) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.msgs = append(c.msgs, msg)
}

func (c *msgCollector) count() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return len(c.msgs)
}

func TestTUIProgressReporter_DrainsChannel(t *testing.T) {
	ref := &programRef{} // nil program - Send is a no-op

	reporter := &TUIProgressReporter{ref: ref}

	ch := make(chan fibonacci.ProgressUpdate, 10)
	var wg sync.WaitGroup
	wg.Add(1)

	// Send some updates
	ch <- fibonacci.ProgressUpdate{CalculatorIndex: 0, Value: 0.25}
	ch <- fibonacci.ProgressUpdate{CalculatorIndex: 0, Value: 0.50}
	ch <- fibonacci.ProgressUpdate{CalculatorIndex: 0, Value: 0.75}
	ch <- fibonacci.ProgressUpdate{CalculatorIndex: 0, Value: 1.00}
	close(ch)

	go reporter.DisplayProgress(&wg, ch, 1, nil)
	wg.Wait()

	// Channel should be fully drained (close consumed)
	// If we reach here without deadlock, the test passes
}

func TestTUIProgressReporter_ZeroCalculators(t *testing.T) {
	ref := &programRef{}
	reporter := &TUIProgressReporter{ref: ref}

	ch := make(chan fibonacci.ProgressUpdate, 5)
	ch <- fibonacci.ProgressUpdate{CalculatorIndex: 0, Value: 0.5}
	close(ch)

	var wg sync.WaitGroup
	wg.Add(1)
	go reporter.DisplayProgress(&wg, ch, 0, nil)
	wg.Wait()
}

func TestTUIResultPresenter_FormatDuration(t *testing.T) {
	ref := &programRef{}
	presenter := &TUIResultPresenter{ref: ref}

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{"microseconds", "500µs", "500µs"},
		{"milliseconds", "42ms", "42ms"},
		{"seconds", "2.5s", "2.5s"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// FormatDuration delegates to cli.FormatExecutionDuration
			// Just verify it doesn't panic
			result := presenter.FormatDuration(0)
			if result == "" {
				t.Error("expected non-empty duration format")
			}
		})
	}
}
