// The demo seeds Avery and Blake, then asks nudges which line to print.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	nudges "github.com/plgkit/nudges/packages/go"
	plgkit "github.com/plgkit/personas/packages/go"
	personanudges "github.com/plgkit/personas/spec/examples/nudges"
)

var show = []string{"avery_blocked", "blake_champion"}

func main() {
	if err := run(os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
}

func run(w io.Writer) error {
	root, err := repoRoot()
	if err != nil {
		return err
	}
	raw, err := os.ReadFile(filepath.Join(root, "spec", "fixtures", "cases.json"))
	if err != nil {
		return err
	}
	var fixture struct {
		CalculatedAt string `json:"calculated_at"`
		Cases        []struct {
			Name    string           `json:"name"`
			UserID  string           `json:"user_id"`
			Events  []map[string]any `json:"events"`
			Persona string           `json:"persona"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &fixture); err != nil {
		return err
	}
	examples := filepath.Join(root, "spec", "examples")
	rules, err := plgkit.LoadRules(filepath.Join(examples, "personas.yml"))
	if err != nil {
		return err
	}
	messages, err := personanudges.LoadMessages(filepath.Join(examples, "nudges", "messages"))
	if err != nil {
		return err
	}
	byName := map[string]int{}
	for i, item := range fixture.Cases {
		byName[item.Name] = i
	}
	db, err := plgkit.Connect("sqlite:///:memory:")
	if err != nil {
		return err
	}
	defer db.Close()
	if err := plgkit.Migrate(db); err != nil {
		return err
	}
	nudgeDB, err := nudges.Connect("sqlite:///:memory:")
	if err != nil {
		return err
	}
	defer nudgeDB.Close()
	if err := nudges.Migrate(nudgeDB); err != nil {
		return err
	}
	for _, name := range show {
		item := fixture.Cases[byName[name]]
		for _, event := range item.Events {
			action, _ := event["action"].(string)
			occurred, _ := event["occurred_at"].(string)
			stored, err := plgkit.Track(item.UserID, action, map[string]any{"occurred_at": occurred}, db, fixture.CalculatedAt)
			if err != nil {
				return err
			}
			if !stored {
				return fmt.Errorf("Could not store %s for %s.", action, item.UserID)
			}
		}
	}
	if _, err := plgkit.Calculate(db, fixture.CalculatedAt, "", &rules); err != nil {
		return err
	}
	audiences := personanudges.Bind(db)
	for _, name := range show {
		item := fixture.Cases[byName[name]]
		result, err := plgkit.Persona(item.UserID, db)
		if err != nil {
			return err
		}
		if result.Persona != item.Persona {
			return fmt.Errorf("%s is %s, expected %s.", item.UserID, result.Persona, item.Persona)
		}
		shown, err := nudges.Decide("home", map[string]any{
			"user": map[string]any{"id": item.UserID},
		}, messages, nudges.Options{DB: nudgeDB, Audiences: audiences})
		if err != nil {
			return err
		}
		if len(shown) != 1 {
			return fmt.Errorf("%s matched %d nudges.", item.UserID, len(shown))
		}
		props, _ := shown[0]["render_props"].(map[string]any)
		body, _ := props["body"].(string)
		if body == "" {
			return fmt.Errorf("%s nudge has no body.", item.UserID)
		}
		label := item.UserID
		if label != "" {
			label = strings.ToUpper(label[:1]) + label[1:]
		}
		fmt.Fprintf(w, "%-8s %-12s %s\n", label, result.Persona, body)
	}
	return nil
}

func repoRoot() (string, error) {
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
			return "", fmt.Errorf("Could not find the personas repo.")
		}
		dir = parent
	}
}
