package main

import (
	"os"

	plgkit "github.com/plgkit/personas/packages/go"
)

func main() {
	os.Exit(plgkit.RunCLI(os.Args[1:]))
}
