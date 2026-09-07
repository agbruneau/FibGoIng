package cli

import (
	"testing"

	"github.com/agbruneau/FibGo/internal/testutil"
	"github.com/agbruneau/FibGo/internal/ui"
)

func TestCLIColorProvider(t *testing.T) {
	// NO_COLOR must be absent for colors to be enabled (InitTheme follows the
	// no-color.org spec, where presence alone disables them) and it may well be
	// set in the developer's or CI environment. testutil.Unsetenv removes it and
	// registers the restore; it also makes this test unavailable to t.Parallel,
	// which is correct for anything touching the process environment
	// (audit TST-02).
	testutil.Unsetenv(t, "NO_COLOR")

	// Initialize theme to ensure we get codes
	ui.InitTheme(false)

	provider := CLIColorProvider{}

	// Test Yellow
	if provider.Yellow() == "" {
		t.Error("Yellow should return a color code when colors are enabled")
	}
	// We just want to ensure it calls the function
	_ = provider.Yellow()

	// Test Reset
	_ = provider.Reset()

	// Test with NoColor
	ui.InitTheme(true)
	if provider.Yellow() != "" {
		t.Error("Yellow should be empty when NoColor is true")
	}
	if provider.Reset() != "" {
		t.Error("Reset should be empty when NoColor is true")
	}
}
