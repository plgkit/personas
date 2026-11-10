package plgkit

import (
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

var defaultPolicy = map[string]int{
	"lookback_days":   14,
	"silence_days":    7,
	"champion_min":    1,
	"power_user_min":  8,
	"implementer_min": 2,
}

var policyKeys = []string{
	"lookback_days",
	"silence_days",
	"champion_min",
	"power_user_min",
	"implementer_min",
}

func DefaultPolicy() map[string]int {
	return copyPolicy(defaultPolicy)
}

func defaultConfigPath() string {
	candidate := filepath.Join("plgkit", "personas", "config.yml")
	info, err := os.Stat(candidate)
	if err == nil && !info.IsDir() {
		return candidate
	}
	return ""
}

func LoadPolicy(path string) (map[string]int, error) {
	if path == "" {
		path = defaultConfigPath()
	}
	if path == "" {
		return NormalizePolicy(nil)
	}
	raw, err := readFlat(path)
	if err != nil {
		return nil, err
	}
	allowed := map[string]bool{"database_url_env": true}
	for _, key := range policyKeys {
		allowed[key] = true
	}
	var unknown []string
	for key := range raw {
		if !allowed[key] {
			unknown = append(unknown, key)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, fail("Unknown config key: " + strings.Join(unknown, ", ") + ".")
	}
	values := map[string]any{}
	for _, key := range policyKeys {
		if value, ok := raw[key]; ok {
			values[key] = value
		}
	}
	return NormalizePolicy(values)
}

func NormalizePolicy(policy map[string]any) (map[string]int, error) {
	merged := copyPolicy(defaultPolicy)
	if policy == nil {
		policy = map[string]any{}
	}
	allowed := map[string]bool{}
	for _, key := range policyKeys {
		allowed[key] = true
	}
	var unknown []string
	for key := range policy {
		if !allowed[key] {
			unknown = append(unknown, key)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, fail("Unknown config key: " + strings.Join(unknown, ", ") + ".")
	}
	for _, key := range policyKeys {
		if value, ok := policy[key]; ok {
			number, err := positiveInt(key, value)
			if err != nil {
				return nil, err
			}
			merged[key] = number
		}
	}
	if merged["silence_days"] >= merged["lookback_days"] {
		return nil, fail("silence_days must be smaller than lookback_days.")
	}
	return merged, nil
}

func copyPolicy(source map[string]int) map[string]int {
	out := map[string]int{}
	for key, value := range source {
		out[key] = value
	}
	return out
}

func positiveInt(key string, value any) (int, error) {
	switch number := value.(type) {
	case int:
		if number < 1 {
			return 0, fail(key + " must be a whole number of 1 or more.")
		}
		return number, nil
	case int64:
		if number < 1 {
			return 0, fail(key + " must be a whole number of 1 or more.")
		}
		return int(number), nil
	case float64:
		if math.IsNaN(number) || math.IsInf(number, 0) || number != math.Trunc(number) || number < 1 || number > math.MaxInt {
			return 0, fail(key + " must be a whole number of 1 or more.")
		}
		return int(number), nil
	case string:
		if number == "" || strings.TrimLeft(number, "0123456789") != "" || !digits(number) {
			return 0, fail(key + " must be a whole number of 1 or more.")
		}
		parsed, err := strconv.Atoi(number)
		if err != nil || parsed < 1 {
			return 0, fail(key + " must be a whole number of 1 or more.")
		}
		return parsed, nil
	default:
		return 0, fail(key + " must be a whole number of 1 or more.")
	}
}

func digits(value string) bool {
	if value == "" {
		return false
	}
	for _, r := range value {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}
