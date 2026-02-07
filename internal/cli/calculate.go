package cli

import (
	"fmt"
	"io"
	"math"
	"runtime"

	"github.com/agbru/fibcalc/internal/config"
	"github.com/agbru/fibcalc/internal/fibonacci"
	"github.com/agbru/fibcalc/internal/ui"
)

// GetCalculatorsToRun determines which calculators should be executed based on
// the configuration. Returns calculators in alphabetically sorted order for
// consistent, reproducible behavior.
//
// Parameters:
//   - cfg: The application configuration containing the algorithm selection.
//   - factory: The calculator factory to retrieve implementations from.
//
// Returns:
//   - []fibonacci.Calculator: A slice of calculators to execute.
func GetCalculatorsToRun(cfg config.AppConfig, factory fibonacci.CalculatorFactory) []fibonacci.Calculator {
	if cfg.Algo == "all" {
		keys := factory.List() // List() returns sorted keys
		calculators := make([]fibonacci.Calculator, 0, len(keys))
		for _, k := range keys {
			if calc, err := factory.Get(k); err == nil {
				calculators = append(calculators, calc)
			}
		}
		return calculators
	}
	if calc, err := factory.Get(cfg.Algo); err == nil {
		return []fibonacci.Calculator{calc}
	}
	return nil
}

// PrintExecutionConfig displays the current execution configuration to the user.
// It shows the target Fibonacci number, timeout, environment details, and
// optimization thresholds.
//
// Parameters:
//   - cfg: The application configuration.
//   - out: The writer for standard output.
func PrintExecutionConfig(cfg config.AppConfig, out io.Writer) {
	fmt.Fprintf(out, "--- Execution Configuration ---\n")
	fmt.Fprintf(out, "Calculating %sF(%d)%s with a timeout of %s%s%s.\n",
		ui.ColorMagenta(), cfg.N, ui.ColorReset(), ui.ColorYellow(), cfg.Timeout, ui.ColorReset())
	fmt.Fprintf(out, "Environment: %s%d%s logical processors, Go %s%s%s.\n",
		ui.ColorCyan(), runtime.NumCPU(), ui.ColorReset(), ui.ColorCyan(), runtime.Version(), ui.ColorReset())
	fmt.Fprintf(out, "Optimization thresholds: Parallelism=%s%d%s bits, FFT=%s%d%s bits.\n",
		ui.ColorCyan(), cfg.Threshold, ui.ColorReset(), ui.ColorCyan(), cfg.FFTThreshold, ui.ColorReset())
}

// PrintFeasibilityWarning checks if the requested computation is likely infeasible
// and prints a warning. F(n) has approximately n*log10(φ) ≈ n*0.20898 decimal digits
// and n*log2(φ) ≈ n*0.6942 bits. The result alone requires n*0.6942/8 bytes of RAM,
// and temporary variables multiply this by ~6x.
func PrintFeasibilityWarning(cfg config.AppConfig, out io.Writer) {
	// Estimate result size
	resultBits := float64(cfg.N) * math.Log2(math.Phi)
	resultDigits := float64(cfg.N) * math.Log10(math.Phi)
	resultMemGB := resultBits / 8 / (1024 * 1024 * 1024)
	// Working memory needs ~6x the result size (FK, FK1, T1-T4)
	workingMemGB := resultMemGB * 6

	// Warn if result exceeds 1 GB of RAM or 1 billion digits
	if resultDigits > 1e9 || workingMemGB > 1 {
		fmt.Fprintf(out, "\n%s⚠  WARNING: F(%d) will have ~%.0f billion digits (~%.1f GB result).%s\n",
			ui.ColorYellow(), cfg.N, resultDigits/1e9, resultMemGB, ui.ColorReset())
		fmt.Fprintf(out, "%s   Estimated working memory: ~%.1f GB. This computation may exceed your timeout (%s) and available RAM.%s\n",
			ui.ColorYellow(), workingMemGB, cfg.Timeout, ui.ColorReset())
		fmt.Fprintf(out, "%s   Consider using a smaller N or increasing --timeout.%s\n\n",
			ui.ColorYellow(), ui.ColorReset())
	}
}

// PrintExecutionMode displays the execution mode (single algorithm vs comparison).
//
// Parameters:
//   - calculators: The slice of calculators that will be executed.
//   - out: The writer for standard output.
func PrintExecutionMode(calculators []fibonacci.Calculator, out io.Writer) {
	var modeDesc string
	if len(calculators) > 1 {
		modeDesc = "Parallel comparison of all algorithms"
	} else {
		modeDesc = fmt.Sprintf("Single calculation with the %s%s%s algorithm",
			ui.ColorGreen(), calculators[0].Name(), ui.ColorReset())
	}
	fmt.Fprintf(out, "Execution mode: %s.\n", modeDesc)
	fmt.Fprintf(out, "\n--- Starting Execution ---\n")
}

