// Audience checks a nudge can call.
//
// Copy this file next to your nudge messages. A message lists one of these
// names under audience.require_all. Pass the map Bind returns as Decide's
// Audiences option. The other four labels match neither function.
package personanudges

import (
	"database/sql"
	"os"
	"path/filepath"
	"runtime"

	plgkit "github.com/plgkit/personas/packages/go"
	"gopkg.in/yaml.v3"
)

// Bind returns the two checks. Pass db and now when the clock or database is pinned.
// Nil mapping and policy load plgkit/personas/*.yml, then the sample files beside this one.
func Bind(db *sql.DB, now string, mapping map[string]string, policy map[string]any) map[string]func(map[string]any) bool {
	label := func(ctx map[string]any) string {
		userID := userID(ctx)
		if userID == "" {
			return "unknown"
		}
		chosenMapping := mapping
		chosenPolicy := policy
		if chosenMapping == nil || chosenPolicy == nil {
			foundMapping, foundPolicy := fromFiles()
			if chosenMapping == nil {
				chosenMapping = foundMapping
			}
			if chosenPolicy == nil {
				chosenPolicy = foundPolicy
			}
		}
		result, err := plgkit.Persona(userID, db, now, chosenMapping, chosenPolicy)
		if err != nil {
			return "unknown"
		}
		return result.Persona
	}
	return map[string]func(map[string]any) bool{
		"persona_is_blocked":  func(ctx map[string]any) bool { return label(ctx) == "blocked" },
		"persona_is_champion": func(ctx map[string]any) bool { return label(ctx) == "champion" },
	}
}

// LoadMessages reads every .yml file in dir and sets id from the file name.
func LoadMessages(dir string) ([]map[string]any, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	messages := []map[string]any{}
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || len(name) < 5 || name[len(name)-4:] != ".yml" {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return nil, err
		}
		var message map[string]any
		if err := yaml.Unmarshal(raw, &message); err != nil {
			return nil, err
		}
		message["id"] = name[:len(name)-4]
		messages = append(messages, message)
	}
	return messages, nil
}

func userID(ctx map[string]any) string {
	user, ok := ctx["user"].(map[string]any)
	if !ok {
		return ""
	}
	id, _ := user["id"].(string)
	return id
}

func fromFiles() (map[string]string, map[string]any) {
	mappingPath := firstFile("mapping.yml")
	configPath := firstFile("config.yml")
	var mapping map[string]string
	var policy map[string]any
	if mappingPath != "" {
		loaded, err := plgkit.LoadMapping(mappingPath)
		if err == nil {
			mapping = loaded
		}
	}
	if configPath != "" {
		loaded, err := plgkit.LoadPolicy(configPath)
		if err == nil {
			policy = map[string]any{}
			for key, value := range loaded {
				policy[key] = value
			}
		}
	}
	return mapping, policy
}

func firstFile(name string) string {
	app := filepath.Join("plgkit", "personas", name)
	if isFile(app) {
		return app
	}
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return ""
	}
	sample := filepath.Join(filepath.Dir(file), "..", name)
	if isFile(sample) {
		return sample
	}
	return ""
}

func isFile(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}
