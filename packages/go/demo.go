package plgkit

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

var demoLines = map[string]string{
	"blocked":  "Want help with the step you stopped on?",
	"champion": "Bring in the person you invited.",
}

var demoShow = []string{"avery_blocked", "blake_champion"}

func PrintDemo(w io.Writer) error {
	root, err := findRepo()
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
	mapping, err := LoadMapping(filepath.Join(examples, "mapping.yml"))
	if err != nil {
		return err
	}
	policyInts, err := LoadPolicy(filepath.Join(examples, "config.yml"))
	if err != nil {
		return err
	}
	policy := map[string]any{}
	for key, value := range policyInts {
		policy[key] = value
	}
	byName := map[string]int{}
	for i, item := range fixture.Cases {
		byName[item.Name] = i
	}
	db, err := Connect("sqlite:///:memory:")
	if err != nil {
		return err
	}
	defer db.Close()
	if err := Migrate(db); err != nil {
		return err
	}
	for _, name := range demoShow {
		item := fixture.Cases[byName[name]]
		for _, event := range item.Events {
			action, _ := event["action"].(string)
			occurred, _ := event["occurred_at"].(string)
			stored, err := Track(item.UserID, action, map[string]any{"occurred_at": occurred}, db, fixture.CalculatedAt)
			if err != nil {
				return err
			}
			if !stored {
				return fail("Could not store " + action + " for " + item.UserID + ".")
			}
		}
		result, err := Persona(item.UserID, db, fixture.CalculatedAt, mapping, policy)
		if err != nil {
			return err
		}
		if result.Persona != item.Persona {
			return fail(item.UserID + " is " + result.Persona + ", expected " + item.Persona + ".")
		}
		line, ok := demoLines[result.Persona]
		if !ok {
			return fail("No demo line for " + result.Persona + ".")
		}
		label := item.UserID
		if label != "" {
			label = strings.ToUpper(label[:1]) + label[1:]
		}
		fmt.Fprintf(w, "%-8s %-12s %s\n", label, result.Persona, line)
	}
	return nil
}

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
