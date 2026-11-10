package plgkit

import (
	"os"
	"strings"
)

func readFlat(path string) (map[string]string, error) {
	text, err := os.ReadFile(path)
	if err != nil {
		return nil, fail("Could not read " + path + ".")
	}
	found := map[string]string{}
	for _, raw := range strings.Split(string(text), "\n") {
		raw = strings.TrimRight(raw, "\r")
		if strings.HasPrefix(raw, " ") || strings.HasPrefix(raw, "\t") {
			if strings.TrimSpace(raw) != "" {
				return nil, fail(path + " must be a flat key: value file.")
			}
			continue
		}
		line := raw
		if i := strings.Index(line, "#"); i >= 0 {
			line = line[:i]
		}
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		colon := strings.Index(line, ":")
		if colon < 0 {
			return nil, fail(path + " must be a flat key: value file.")
		}
		key := strings.TrimSpace(line[:colon])
		value := strings.TrimSpace(line[colon+1:])
		if len(value) >= 2 && (value[0] == '\'' || value[0] == '"') && value[0] == value[len(value)-1] {
			value = value[1 : len(value)-1]
		}
		if key == "" {
			return nil, fail(path + " has an empty key.")
		}
		if value == "" {
			return nil, fail(key + " in " + path + " needs a value.")
		}
		if _, ok := found[key]; ok {
			return nil, fail(key + " is set more than once in " + path + ".")
		}
		found[key] = value
	}
	return found, nil
}
