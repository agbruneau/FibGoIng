// Package main is the entry point for the fibcalc CLI. It handles version/help
// flags, builds the application from config, and runs the main loop.
package main

import (
	"context"
	"io"
	"os"

	"github.com/agbru/fibcalc/internal/app"
)

// exitVersion is the sentinel exit code returned when --version is handled.
const exitVersion = -1

// main parses arguments, builds the application, and runs it; exit code
// reflects success, help, or error.
func main() {
	code := run(os.Args, os.Stdout, os.Stderr)
	if code >= 0 {
		os.Exit(code)
	}
}

// run contains the core logic extracted from main for testability.
// It returns an exit code: 0 for success, positive for errors,
// or exitVersion (-1) when --version was handled (no os.Exit needed).
func run(args []string, stdout, stderr io.Writer) int {
	if app.HasVersionFlag(args[1:]) {
		app.PrintVersion(stdout)
		return exitVersion
	}

	application, err := app.New(args, stderr)
	if err != nil {
		if app.IsHelpError(err) {
			return 0
		}
		return 1
	}

	return application.Run(context.Background(), stdout)
}
