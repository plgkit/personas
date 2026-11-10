package plgkit

import (
	"os"
	"path/filepath"
)

func findRepo() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "spec", "fixtures", "cases.json")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fail("Could not find the personas repo.")
		}
		dir = parent
	}
}
