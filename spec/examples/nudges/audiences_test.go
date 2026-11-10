package personanudges

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	plgkit "github.com/plgkit/personas/packages/go"
)

func TestMessages(t *testing.T) {
	messages, err := LoadMessages("messages")
	if err != nil {
		t.Fatal(err)
	}
	if len(messages) != 2 {
		t.Fatalf("%d messages", len(messages))
	}
	want := map[string]string{
		"20261110150400-home-blocked-help":    "Want help with the step you stopped on?",
		"20261110150401-home-champion-invite": "Bring in the person you invited.",
	}
	for _, message := range messages {
		id, _ := message["id"].(string)
		props, _ := message["render_props"].(map[string]any)
		body, _ := props["body"].(string)
		if want[id] != body {
			t.Fatalf("%s body %q", id, body)
		}
	}
}

func TestAudiencesFollowTheStoredWinner(t *testing.T) {
	root := repoRoot(t)
	raw, err := os.ReadFile(filepath.Join(root, "spec", "fixtures", "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Rules json.RawMessage `json:"rules"`
		Cases []struct {
			Name         string           `json:"name"`
			UserID       string           `json:"user_id"`
			Persona      string           `json:"persona"`
			CalculatedAt string           `json:"calculated_at"`
			Events       []map[string]any `json:"events"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatal(err)
	}
	var parsed any
	if err := json.Unmarshal(fixture.Rules, &parsed); err != nil {
		t.Fatal(err)
	}
	rules, err := plgkit.NormalizeRules(parsed)
	if err != nil {
		t.Fatal(err)
	}
	for _, item := range fixture.Cases {
		switch item.Name {
		case "avery_blocked", "blake_champion", "developer_member", "empty":
		default:
			continue
		}
		db, err := plgkit.Connect("sqlite:///:memory:")
		if err != nil {
			t.Fatal(err)
		}
		if err := plgkit.Migrate(db); err != nil {
			t.Fatal(err)
		}
		for _, event := range item.Events {
			action, _ := event["action"].(string)
			occurred, _ := event["occurred_at"].(string)
			stored, err := plgkit.Track(item.UserID, action, map[string]any{"occurred_at": occurred}, db, item.CalculatedAt)
			if err != nil || !stored {
				t.Fatalf("%s %s %v", item.Name, action, err)
			}
		}
		if _, err := plgkit.Calculate(db, item.CalculatedAt, item.UserID, &rules); err != nil {
			t.Fatal(item.Name, err)
		}
		checks := Bind(db)
		ctx := map[string]any{"user": map[string]any{"id": item.UserID}}
		if checks["persona_is_blocked"](ctx) != (item.Persona == "blocked") {
			t.Fatalf("%s blocked check", item.Name)
		}
		if checks["persona_is_champion"](ctx) != (item.Persona == "champion") {
			t.Fatalf("%s champion check", item.Name)
		}
		db.Close()
	}
}

func repoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "spec", "fixtures", "cases.json")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("Could not find the personas repo.")
		}
		dir = parent
	}
}
