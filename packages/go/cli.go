package plgkit

import (
	"fmt"
	"os"
)

func RunCLI(args []string) int {
	if len(args) == 0 || args[0] == "-h" || args[0] == "--help" {
		usage()
		if len(args) == 0 {
			return 1
		}
		return 0
	}
	if args[0] != "migrate" {
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", args[0])
		usage()
		return 1
	}
	if err := Migrate(nil); err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 1
	}
	fmt.Println("Migrations are up to date.")
	return 0
}

func usage() {
	fmt.Fprintln(os.Stderr, "Usage: plgkit-personas migrate")
}
