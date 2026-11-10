package plgkit

import (
	"os"
	"path/filepath"
	"strings"
)

var categories = []string{"core_action", "invite_sent", "setup_step"}

func categorySet() map[string]bool {
	found := map[string]bool{}
	for _, name := range categories {
		found[name] = true
	}
	return found
}

func defaultMappingPath() string {
	candidate := filepath.Join("plgkit", "personas", "mapping.yml")
	info, err := os.Stat(candidate)
	if err == nil && !info.IsDir() {
		return candidate
	}
	return ""
}

func LoadMapping(path string) (map[string]string, error) {
	if path == "" {
		path = defaultMappingPath()
	}
	if path == "" {
		return map[string]string{}, nil
	}
	raw, err := readFlat(path)
	if err != nil {
		return nil, err
	}
	return NormalizeMapping(raw)
}

func NormalizeMapping(mapping map[string]string) (map[string]string, error) {
	if mapping == nil {
		return map[string]string{}, nil
	}
	allowed := categorySet()
	cleaned := map[string]string{}
	for action, category := range mapping {
		if strings.TrimSpace(action) == "" {
			return nil, fail("mapping actions must be non-empty strings.")
		}
		if !allowed[category] {
			return nil, fail(action + " maps to '" + category + "'. Use one of: " + strings.Join(categories, ", ") + ".")
		}
		cleaned[action] = category
	}
	return cleaned, nil
}
