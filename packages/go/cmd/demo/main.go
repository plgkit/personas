package main

import (
	"fmt"
	"os"

	plgkit "github.com/plgkit/personas/packages/go"
)

func main() {
	if err := plgkit.PrintDemo(os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
}
