// Audience checks a nudge can call.
//
// Copy this file next to your nudge messages. Each function calls PersonaIs
// with the persona name from personas.yml. Add one function when you add a message.
package personanudges

import (
	"os"
	"path/filepath"
	"strings"

	"database/sql"

	plgkit "github.com/plgkit/personas/packages/go"
	"gopkg.in/yaml.v3"
)

// Bind returns the checks for the sample messages. Pass db when the database is pinned.
func Bind(db *sql.DB) map[string]func(map[string]any) bool {
	check := func(name string) func(map[string]any) bool {
		return func(ctx map[string]any) bool {
			userID := userID(ctx)
			if userID == "" {
				return false
			}
			ok, err := plgkit.PersonaIs(userID, name, db)
			return err == nil && ok
		}
	}
	return map[string]func(map[string]any) bool{
		"persona_is_blocked":  check("blocked"),
		"persona_is_champion": check("champion"),
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
		if entry.IsDir() || !strings.HasSuffix(name, ".yml") {
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
		message["id"] = strings.TrimSuffix(name, ".yml")
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
