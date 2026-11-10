package plgkit

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestExampleFileMatchesFixture(t *testing.T) {
	fixture := loadFixture(t)
	root := repoFromTest(t)
	loaded, err := LoadRules(filepath.Join(root, "spec", "examples", "personas.yml"))
	if err != nil {
		t.Fatal(err)
	}
	fromFixture, err := rulesFromRaw(fixture.Rules)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(loaded, fromFixture) {
		t.Fatalf("example rules differ from the fixture")
	}
}

func TestSharedCases(t *testing.T) {
	fixture := loadFixture(t)
	names := map[string]bool{}
	for _, item := range fixture.Cases {
		names[item.Name] = true
		raw := fixture.Rules
		if len(item.Rules) > 0 && string(item.Rules) != "null" {
			raw = item.Rules
		}
		rules, err := rulesFromRaw(raw)
		if err != nil {
			t.Fatal(item.Name, err)
		}
		result, err := Judge(item.UserID, item.Events, item.Traits, rules, item.CalculatedAt)
		if err != nil {
			t.Fatal(item.Name, err)
		}
		if result.Persona != item.Persona {
			t.Fatalf("%s persona %s", item.Name, result.Persona)
		}
		if stringsJoin(result.Matched) != stringsJoin(item.Matched) {
			t.Fatalf("%s matched %#v", item.Name, result.Matched)
		}
		if !sameReasons(result.Reasons, item.Reasons) {
			t.Fatalf("%s reasons %#v want %#v", item.Name, result.Reasons, item.Reasons)
		}
		if result.CalculatedAt != item.CalculatedAt {
			t.Fatalf("%s calculated_at %s", item.Name, result.CalculatedAt)
		}
	}
	if !names["developer_member"] || !names["avery_blocked"] || !names["blake_champion"] {
		t.Fatal("missing demo cases")
	}
}

func TestBadRules(t *testing.T) {
	_, err := NormalizeRules(map[string]any{"personas": []any{map[string]any{"name": "a", "require_all": []any{}}}})
	if err == nil {
		t.Fatal("missing priority")
	}
	_, err = NormalizeRules(map[string]any{"mystery": 1})
	if err == nil {
		t.Fatal("unknown key")
	}
}

type fixtureFile struct {
	Rules json.RawMessage `json:"rules"`
	Cases []fixtureCase   `json:"cases"`
}

type fixtureCase struct {
	Name         string            `json:"name"`
	UserID       string            `json:"user_id"`
	Events       []map[string]any  `json:"events"`
	Traits       map[string]string `json:"traits"`
	Rules        json.RawMessage   `json:"rules"`
	Persona      string            `json:"persona"`
	Matched      []string          `json:"matched"`
	Reasons      []Reason          `json:"reasons"`
	CalculatedAt string            `json:"calculated_at"`
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

func rulesFromRaw(raw json.RawMessage) (Rules, error) {
	var parsed any
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return Rules{}, err
	}
	return NormalizeRules(parsed)
}

func repoFromTest(t *testing.T) string {
	t.Helper()
	root, err := findRepo()
	if err != nil {
		t.Fatal(err)
	}
	return root
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
