package tui

import (
	"context"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/agbru/fibcalc/internal/config"
	apperrors "github.com/agbru/fibcalc/internal/errors"
)

// mockCalculator implements fibonacci.Calculator for testing.
type mockCalculator struct {
	name string
}

func (m mockCalculator) Calculate(_ context.Context, _ chan<- interface{}, _ int, _ uint64, _ interface{}) (interface{}, error) {
	return nil, nil
}

func (m mockCalculator) Name() string { return m.name }

func TestNewModel(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg := config.AppConfig{N: 1000, Timeout: time.Minute}
	model := NewModel(ctx, cancel, nil, cfg, "v0.1.0")

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
