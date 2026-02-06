package tui

import (
	"context"
	"math/big"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/agbru/fibcalc/internal/config"
	apperrors "github.com/agbru/fibcalc/internal/errors"
	"github.com/agbru/fibcalc/internal/fibonacci"
	"github.com/agbru/fibcalc/internal/orchestration"
)

// mockCalculator implements fibonacci.Calculator for testing.
type mockCalculator struct {
	name string
}

func (m mockCalculator) Calculate(_ context.Context, _ chan<- fibonacci.ProgressUpdate, _ int, _ uint64, _ fibonacci.Options) (*big.Int, error) {
	return big.NewInt(0), nil
}

func (m mockCalculator) Name() string { return m.name }

// Verify interface compliance at compile time.
var _ fibonacci.Calculator = mockCalculator{}

func newTestModel(t *testing.T) Model {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)
	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	return NewModel(ctx, cancel, nil, cfg, "v0.1.0")
}

func newTestModelWithSize(t *testing.T, w, h int) Model {
	t.Helper()
	m := newTestModel(t)
	updated, _ := m.Update(tea.WindowSizeMsg{Width: w, Height: h})
	return updated.(Model)
}

func TestNewModel(t *testing.T) {
	model := newTestModel(t)

	if model.paused {
		t.Error("expected model to not be paused initially")
	}
	if model.done {
		t.Error("expected model to not be done initially")
	}
	if model.exitCode != apperrors.ExitSuccess {
		t.Errorf("expected exit code %d, got %d", apperrors.ExitSuccess, model.exitCode)
	}
}

func TestNewModel_WithCalculators(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	calcs := []fibonacci.Calculator{
		mockCalculator{name: "Fast Doubling"},
		mockCalculator{name: "Matrix"},
	}
	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, calcs, cfg, "v1.0.0")

	if len(model.calculators) != 2 {
		t.Errorf("expected 2 calculators, got %d", len(model.calculators))
	}
}

func TestModel_Update_WindowSize(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	msg := tea.WindowSizeMsg{Width: 120, Height: 40}
	updated, cmd := model.Update(msg)
	m := updated.(Model)

	if m.width != 120 {
		t.Errorf("expected width 120, got %d", m.width)
	}
	if m.height != 40 {
		t.Errorf("expected height 40, got %d", m.height)
	}
	if cmd != nil {
		t.Error("expected no command from window size update")
	}
}

func TestModel_Update_ProgressMsg(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	// Set size first so viewport is initialized
	sized, _ := model.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
	m := sized.(Model)

	msg := ProgressMsg{
		CalculatorIndex: 0,
		Value:           0.5,
		AverageProgress: 0.5,
		ETA:             30 * time.Second,
	}
	updated, _ := m.Update(msg)
	result := updated.(Model)

	if len(result.chart.dataPoints) == 0 {
		t.Error("expected chart to have data points after progress update")
	}
}

func TestModel_Update_ProgressMsg_Paused(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")
	model.paused = true

	msg := ProgressMsg{
		CalculatorIndex: 0,
		Value:           0.5,
		AverageProgress: 0.5,
		ETA:             30 * time.Second,
	}
	updated, _ := model.Update(msg)
	result := updated.(Model)

	if len(result.chart.dataPoints) != 0 {
		t.Error("expected chart to have no data points when paused")
	}
}

func TestModel_Update_CalculationComplete(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	msg := CalculationCompleteMsg{ExitCode: 0}
	updated, _ := model.Update(msg)
	result := updated.(Model)

	if !result.done {
		t.Error("expected model to be done after calculation complete")
	}
	if result.exitCode != 0 {
		t.Errorf("expected exit code 0, got %d", result.exitCode)
	}
}

func TestModel_Update_ErrorMsg(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	// Set size first
	sized, _ := model.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
	m := sized.(Model)

	msg := ErrorMsg{Err: context.DeadlineExceeded, Duration: time.Second}
	updated, _ := m.Update(msg)
	result := updated.(Model)

	if !result.done {
		t.Error("expected model to be done after error")
	}
	if !result.footer.hasErr {
		t.Error("expected footer to show error state")
	}
}

func TestModel_View_Initializing(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	view := model.View()
	if view != "Initializing..." {
		t.Errorf("expected 'Initializing...' when no size set, got %q", view)
	}
}

func TestModel_View_WithSize(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	sized, _ := model.Update(tea.WindowSizeMsg{Width: 80, Height: 24})
	m := sized.(Model)

	view := m.View()
	if view == "Initializing..." {
		t.Error("expected rendered dashboard, got 'Initializing...'")
	}
	if len(view) == 0 {
		t.Error("expected non-empty view")
	}
}

func TestModel_HandleKey_Pause(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	// Press space to pause
	updated, _ := model.Update(tea.KeyMsg{Type: tea.KeySpace})
	m := updated.(Model)
	if !m.paused {
		t.Error("expected model to be paused after space key")
	}

	// Press space to resume
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeySpace})
	m = updated.(Model)
	if m.paused {
		t.Error("expected model to be unpaused after second space key")
	}
}

func TestModel_HandleKey_Reset(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

	// Set size first
	sized, _ := model.Update(tea.WindowSizeMsg{Width: 80, Height: 24})
	m := sized.(Model)

	// Add some chart data
	m.chart.AddDataPoint(0.5, 0.5, 10*time.Second)

	// Press 'r' to reset
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	result := updated.(Model)

	if len(result.chart.dataPoints) != 0 {
		t.Error("expected chart to be reset after 'r' key")
	}
}

func TestModel_Update_ComparisonResultsMsg(t *testing.T) {
	m := newTestModelWithSize(t, 120, 40)

	msg := ComparisonResultsMsg{
		Results: []orchestration.CalculationResult{
			{Name: "Fast", Duration: 100 * time.Millisecond},
		},
	}
	updated, cmd := m.Update(msg)
	result := updated.(Model)

	if cmd != nil {
		t.Error("expected no command from comparison results")
	}
	if len(result.logs.entries) == 0 {
		t.Error("expected logs to have entries after comparison results")
	}
}

func TestModel_Update_FinalResultMsg(t *testing.T) {
	m := newTestModelWithSize(t, 120, 40)

	msg := FinalResultMsg{
		Result: orchestration.CalculationResult{
			Name:     "Fast",
			Result:   big.NewInt(55),
			Duration: 50 * time.Millisecond,
		},
		N:       10,
		Verbose: true,
	}
	updated, cmd := m.Update(msg)
	result := updated.(Model)

	if cmd != nil {
		t.Error("expected no command from final result")
	}
	if len(result.logs.entries) == 0 {
		t.Error("expected logs to have entries after final result")
	}
}

func TestModel_Update_ProgressDoneMsg(t *testing.T) {
	m := newTestModel(t)

	updated, cmd := m.Update(ProgressDoneMsg{})
	result := updated.(Model)

	if cmd != nil {
		t.Error("expected no command from progress done")
	}
	// ProgressDoneMsg is a no-op, model state should not change
	if result.done {
		t.Error("expected model not to be done after ProgressDoneMsg")
	}
}

func TestModel_Update_ContextCancelledMsg(t *testing.T) {
	m := newTestModel(t)

	msg := ContextCancelledMsg{Err: context.Canceled}
	updated, cmd := m.Update(msg)
	result := updated.(Model)

	if !result.done {
		t.Error("expected model to be done after context cancelled")
	}
	if cmd == nil {
		t.Error("expected tea.Quit command from context cancelled")
	}
}

func TestModel_Update_CalculationComplete_NonZeroExitCode(t *testing.T) {
	m := newTestModel(t)

	msg := CalculationCompleteMsg{ExitCode: apperrors.ExitErrorMismatch}
	updated, _ := m.Update(msg)
	result := updated.(Model)

	if result.exitCode != apperrors.ExitErrorMismatch {
		t.Errorf("expected exit code %d, got %d", apperrors.ExitErrorMismatch, result.exitCode)
	}
	if !result.footer.done {
		t.Error("expected footer to show done state")
	}
}

func TestModel_Update_MemStatsMsg(t *testing.T) {
	m := newTestModel(t)

	msg := MemStatsMsg{
		Alloc:        1024 * 1024 * 10,
		HeapInuse:    1024 * 1024 * 20,
		NumGC:        5,
		NumGoroutine: 12,
	}
	updated, _ := m.Update(msg)
	result := updated.(Model)

	if result.metrics.alloc != msg.Alloc {
		t.Errorf("expected alloc %d, got %d", msg.Alloc, result.metrics.alloc)
	}
}

func TestModel_Update_TickMsg_NotPaused(t *testing.T) {
	m := newTestModel(t)

	updated, cmd := m.Update(TickMsg(time.Now()))
	_ = updated

	// When not paused, should return a batch of sampleMemStatsCmd + tickCmd
	if cmd == nil {
		t.Error("expected commands from tick when not paused")
	}
}

func TestModel_Update_TickMsg_Paused(t *testing.T) {
	m := newTestModel(t)
	m.paused = true

	updated, cmd := m.Update(TickMsg(time.Now()))
	_ = updated

	// When paused, should return only tickCmd (no mem stats sampling)
	if cmd == nil {
		t.Error("expected tick command even when paused")
	}
}

func TestModel_HandleKey_Quit_Q(t *testing.T) {
	m := newTestModel(t)

	_, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	if cmd == nil {
		t.Error("expected tea.Quit command from 'q' key")
	}
}

func TestModel_HandleKey_Quit_CtrlC(t *testing.T) {
	m := newTestModel(t)

	_, cmd := m.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	if cmd == nil {
		t.Error("expected tea.Quit command from Ctrl+C")
	}
}

func TestModel_HandleKey_ScrollKeys(t *testing.T) {
	m := newTestModelWithSize(t, 120, 40)

	// Add enough content to scroll
	for i := 0; i < 50; i++ {
		m.logs.AddProgressEntry(ProgressMsg{CalculatorIndex: 0, Value: float64(i) / 50})
	}

	keys := []tea.KeyMsg{
		{Type: tea.KeyUp},
		{Type: tea.KeyDown},
		{Type: tea.KeyPgUp},
		{Type: tea.KeyPgDown},
		{Type: tea.KeyRunes, Runes: []rune{'k'}},
		{Type: tea.KeyRunes, Runes: []rune{'j'}},
	}
	for _, k := range keys {
		updated, cmd := m.Update(k)
		m = updated.(Model)
		if cmd != nil {
			t.Errorf("expected no command from scroll key %v", k)
		}
	}
}

func TestModel_HandleKey_Unknown(t *testing.T) {
	m := newTestModel(t)

	updated, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'x'}})
	result := updated.(Model)

	if cmd != nil {
		t.Error("expected no command from unknown key")
	}
	if result.paused {
		t.Error("unknown key should not change state")
	}
}

func TestModel_Update_UnknownMsg(t *testing.T) {
	m := newTestModel(t)

	// Send an arbitrary message type
	type unknownMsg struct{}
	updated, cmd := m.Update(unknownMsg{})
	_ = updated

	if cmd != nil {
		t.Error("expected no command from unknown message type")
	}
}

func TestModel_LayoutPanels_VerySmallTerminal(t *testing.T) {
	m := newTestModel(t)

	// Very small terminal — bodyHeight would be negative without the clamp
	updated, _ := m.Update(tea.WindowSizeMsg{Width: 20, Height: 8})
	result := updated.(Model)

	// Should not panic and should render something
	view := result.View()
	if len(view) == 0 {
		t.Error("expected non-empty view for small terminal")
	}
}

func TestModel_LayoutPanels_MinBodyHeight(t *testing.T) {
	m := newTestModel(t)

	// Height = 6 means bodyHeight = 0 -> clamped to 4
	updated, _ := m.Update(tea.WindowSizeMsg{Width: 80, Height: 6})
	result := updated.(Model)

	view := result.View()
	if view == "Initializing..." {
		t.Error("expected rendered dashboard, not initializing")
	}
}

func TestModel_HandleKey_Reset_ClearsMetrics(t *testing.T) {
	m := newTestModelWithSize(t, 80, 24)

	// Set some metrics
	m.metrics.lastUpdate = time.Now().Add(-time.Second)
	m.metrics.UpdateProgress(0.5)

	if m.metrics.speed == 0 {
		t.Fatal("precondition: metrics speed should be non-zero")
	}

	// Reset
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	result := updated.(Model)

	if result.metrics.speed != 0 {
		t.Error("expected metrics speed to be reset to 0")
	}
}

func TestModel_HandleKey_Quit_CancelsContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	m := NewModel(ctx, cancel, nil, cfg, "v1.0.0")

	m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})

	// Context should be cancelled after quit
	select {
	case <-ctx.Done():
		// Good — context was cancelled
	default:
		t.Error("expected context to be cancelled after quit")
	}
}
