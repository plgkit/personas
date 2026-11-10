package plgkit

import (
	"database/sql"
	"strings"
	"time"
)

func Identify(userID string, traits map[string]string, db *sql.DB, now string) error {
	id, err := requireText(userID, "user_id")
	if err != nil {
		return err
	}
	if len(traits) == 0 {
		return fail("traits must be an object of strings.")
	}
	moment := time.Now().UTC()
	if now != "" {
		moment, err = ParseTime(now)
		if err != nil {
			return err
		}
	}
	cleaned := map[string]string{}
	for key, value := range traits {
		if strings.TrimSpace(key) == "" {
			return fail("trait keys must be non-empty strings.")
		}
		cleaned[strings.TrimSpace(key)] = value
	}
	db, err = ensureDB(db)
	if err != nil {
		return err
	}
	stamp := FormatTime(moment)
	for key, value := range cleaned {
		if err := upsertTrait(db, id, key, value, stamp); err != nil {
			return fail("Could not store traits. Run plgkit-personas migrate.")
		}
	}
	return nil
}
