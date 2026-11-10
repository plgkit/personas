package plgkit

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestSharedCases(t *testing.T) {
	fixture := loadFixture(t)
	if !samePolicy(DefaultPolicy(), intsFromAny(fixture.Config)) {
		t.Fatalf("defaults = %#v", DefaultPolicy())
	}
	root := repoFromTest(t)
	mapping, err := LoadMapping(filepath.Join(root, "spec", "examples", "mapping.yml"))
	if err != nil {
		t.Fatal(err)
	}
	if !sameStringMap(mapping, fixture.Mapping) {
		t.Fatalf("mapping = %#v", mapping)
	}
	policy, err := LoadPolicy(filepath.Join(root, "spec", "examples", "config.yml"))
	if err != nil {
		t.Fatal(err)
	}
	if !samePolicy(policy, intsFromAny(fixture.Config)) {
		t.Fatalf("policy = %#v", policy)
	}
	names := map[string]bool{}
	for _, item := range fixture.Cases {
		names[item.Name] = true
		result, err := Judge(item.UserID, item.Events, fixture.Mapping, fixture.Config, item.CalculatedAt)
		if err != nil {
			t.Fatal(item.Name, err)
		}
		if result.Persona != item.Persona {
			t.Fatalf("%s persona %s", item.Name, result.Persona)
		}
		if stringsJoin(result.Matched) != stringsJoin(item.Matched) {
			t.Fatalf("%s matched %#v", item.Name, result.Matched)
		}
		if !samePolicy(result.Counts, item.Counts) {
			t.Fatalf("%s counts %#v", item.Name, result.Counts)
		}
		if !sameReasons(result.Reasons, item.Reasons) {
			t.Fatalf("%s reasons %#v", item.Name, result.Reasons)
		}
		if result.CalculatedAt != item.CalculatedAt {
			t.Fatalf("%s calculated_at %s", item.Name, result.CalculatedAt)
		}
		if len(result.Reasons) > 5 {
			t.Fatalf("%s has %d reasons", item.Name, len(result.Reasons))
		}
	}
	if !names["avery_blocked"] || !names["blake_champion"] {
		t.Fatal("missing demo cases")
	}
}

func TestLowerPowerThreshold(t *testing.T) {
	fixture := loadFixture(t)
	var jordan fixtureCase
	for _, item := range fixture.Cases {
		if item.Name == "evaluator" {
			jordan = item
		}
	}
	policy := map[string]any{}
	for key, value := range fixture.Config {
		policy[key] = value
	}
	policy["power_user_min"] = 2
	result, err := Judge(jordan.UserID, jordan.Events, fixture.Mapping, policy, jordan.CalculatedAt)
	if err != nil {
		t.Fatal(err)
	}
	if result.Persona != "power_user" {
		t.Fatal(result.Persona)
	}
}

type fixtureFile struct {
	Config  map[string]any    `json:"config"`
	Mapping map[string]string `json:"mapping"`
	Cases   []fixtureCase     `json:"cases"`
}

type fixtureCase struct {
	Name         string           `json:"name"`
	UserID       string           `json:"user_id"`
	Events       []map[string]any `json:"events"`
	Persona      string           `json:"persona"`
	Matched      []string         `json:"matched"`
	Counts       map[string]int   `json:"counts"`
	Reasons      []Reason         `json:"reasons"`
	CalculatedAt string           `json:"calculated_at"`
}

func loadFixture(t *testing.T) fixtureFile {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(repoFromTest(t), "spec", "fixtures", "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	var fixture fixtureFile
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	return fixture
}

func repoFromTest(t *testing.T) string {
	t.Helper()
	root, err := findRepo()
	if err != nil {
		t.Fatal(err)
	}
	return root
}

func intsFromAny(values map[string]any) map[string]int {
	out := map[string]int{}
	for key, value := range values {
		number, err := positiveInt(key, value)
		if err != nil {
			continue
		}
		out[key] = number
	}
	return out
}

func samePolicy(left, right map[string]int) bool {
	if len(left) != len(right) {
		return false
	}
	for key, value := range left {
		if right[key] != value {
			return false
		}
	}
	return true
}

func sameStringMap(left, right map[string]string) bool {
	if len(left) != len(right) {
		return false
	}
	for key, value := range left {
		if right[key] != value {
			return false
		}
	}
	return true
}

func sameReasons(left, right []Reason) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func stringsJoin(values []string) string {
	out := ""
	for _, value := range values {
		out += value + "\n"
	}
	return out
}
