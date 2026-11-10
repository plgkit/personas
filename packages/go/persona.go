package plgkit

import "database/sql"

func Persona(userID string, db *sql.DB, now string, mapping map[string]string, policy map[string]any) (Result, error) {
	id, err := requireText(userID, "user_id")
	if err != nil {
		return Result{}, err
	}
	if mapping == nil {
		mapping, err = LoadMapping("")
		if err != nil {
			return Result{}, err
		}
	}
	if policy == nil {
		loaded, err := LoadPolicy("")
		if err != nil {
			return Result{}, err
		}
		policy = map[string]any{}
		for key, value := range loaded {
			policy[key] = value
		}
	}
	database, err := ensureDB(db)
	if err != nil {
		return Result{}, err
	}
	events, err := listEvents(database, id)
	if err != nil {
		return Result{}, err
	}
	return Judge(id, events, mapping, policy, now)
}
