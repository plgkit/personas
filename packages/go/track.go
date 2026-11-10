package plgkit

import (
	"database/sql"
	"encoding/json"
	"strings"
	"time"
)

func Track(userID, action string, metadata any, db *sql.DB, now string) (bool, error) {
	id, err := requireText(userID, "user_id")
	if err != nil {
		return false, err
	}
	verb, err := requireText(action, "action")
	if err != nil {
		return false, err
	}
	var received time.Time
	if now == "" {
		received = time.Now().UTC()
	} else {
		received, err = ParseTime(now)
		if err != nil {
			return false, err
		}
	}
	body, eventID, occurred, err := cleanMetadata(metadata, received)
	if err != nil {
		return false, err
	}
	encoded, err := json.Marshal(body)
	if err != nil {
		return false, fail("metadata must be JSON.")
	}
	database, err := ensureDB(db)
	if err != nil {
		return false, err
	}
	stored, err := insertEvent(database, id, verb, eventID, encoded, FormatTime(occurred), FormatTime(received))
	if err != nil {
		return false, fail("Could not store the event. Run plgkit-personas migrate.")
	}
	return stored, nil
}

func cleanMetadata(metadata any, received time.Time) (map[string]any, *string, time.Time, error) {
	if metadata == nil {
		metadata = map[string]any{}
	}
	encoded, err := json.Marshal(metadata)
	if err != nil {
		return nil, nil, time.Time{}, fail("metadata must be JSON.")
	}
	var body map[string]any
	if err := json.Unmarshal(encoded, &body); err != nil || body == nil {
		return nil, nil, time.Time{}, fail("metadata must be an object.")
	}
	occurred := received
	if raw, ok := body["occurred_at"]; ok {
		text, ok := raw.(string)
		if !ok {
			return nil, nil, time.Time{}, fail("occurred_at must be an ISO-8601 timestamp with a timezone.")
		}
		occurred, err = ParseTime(text)
		if err != nil {
			return nil, nil, time.Time{}, err
		}
	}
	delete(body, "occurred_at")
	var eventID *string
	if raw, ok := body["event_id"]; ok && raw != nil {
		text, ok := raw.(string)
		if !ok {
			return nil, nil, time.Time{}, fail("event_id must be a string.")
		}
		text = strings.TrimSpace(text)
		if text != "" {
			eventID = &text
		}
	}
	delete(body, "event_id")
	return body, eventID, occurred, nil
}

func ensureDB(db *sql.DB) (*sql.DB, error) {
	if db != nil {
		return db, nil
	}
	mu.Lock()
	defer mu.Unlock()
	return openDefaultLocked()
}
