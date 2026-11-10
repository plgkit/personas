package plgkit

import (
	"database/sql"
	"time"
)

type Summary struct {
	Users     int
	Assigned  int
	Unmatched int
}

func Calculate(db *sql.DB, now string, userID string, rules *Rules) (Summary, error) {
	var err error
	db, err = ensureDB(db)
	if err != nil {
		return Summary{}, err
	}
	var loaded Rules
	if rules == nil {
		loaded, err = LoadRules("")
		if err != nil {
			return Summary{}, err
		}
	} else {
		loaded = *rules
	}
	moment := time.Now().UTC()
	if now != "" {
		moment, err = ParseTime(now)
		if err != nil {
			return Summary{}, err
		}
	}
	stamp := FormatTime(moment)
	var userIDs []string
	if userID == "" {
		userIDs, err = listUserIDs(db)
		if err != nil {
			return Summary{}, fail("Could not calculate personas. Run plgkit-personas migrate.")
		}
	} else {
		id, err := requireText(userID, "user_id")
		if err != nil {
			return Summary{}, err
		}
		userIDs = []string{id}
	}
	assigned := 0
	for _, current := range userIDs {
		events, err := listEvents(db, current)
		if err != nil {
			return Summary{}, fail("Could not calculate personas. Run plgkit-personas migrate.")
		}
		traits, err := listTraits(db, current)
		if err != nil {
			return Summary{}, fail("Could not calculate personas. Run plgkit-personas migrate.")
		}
		result, err := Judge(current, events, traits, loaded, stamp)
		if err != nil {
			return Summary{}, err
		}
		if err := writeSnapshot(db, result); err != nil {
			return Summary{}, fail("Could not calculate personas. Run plgkit-personas migrate.")
		}
		if result.Persona != "" {
			assigned++
		}
	}
	return Summary{Users: len(userIDs), Assigned: assigned, Unmatched: len(userIDs) - assigned}, nil
}
