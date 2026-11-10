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
	if args[0] == "migrate" {
		if len(args) != 1 {
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
	if args[0] == "calculate" {
		return runCalculate(args[1:])
	}
	fmt.Fprintf(os.Stderr, "Unknown command: %s\n", args[0])
	usage()
	return 1
}

func usage() {
	fmt.Fprintln(os.Stderr, "Usage: plgkit-personas migrate")
	fmt.Fprintln(os.Stderr, "       plgkit-personas calculate [--user ID] [--now TIMESTAMP]")
}

func runCalculate(args []string) int {
	userID := ""
	now := ""
	for index := 0; index < len(args); index++ {
		flag := args[index]
		if (flag == "--user" || flag == "--now") && index+1 < len(args) {
			if flag == "--user" {
				userID = args[index+1]
			} else {
				now = args[index+1]
			}
			index++
			continue
		}
		usage()
		return 1
	}
	summary, err := Calculate(nil, now, userID, nil)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 1
	}
	fmt.Printf("Calculated %d users. %d assigned. %d unmatched.\n", summary.Users, summary.Assigned, summary.Unmatched)
	return 0
}
