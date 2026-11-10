package plgkit

import "database/sql"

func Persona(userID string, db *sql.DB) (Result, error) {
	id, err := requireText(userID, "user_id")
	if err != nil {
		return Result{}, err
	}
	db, err = ensureDB(db)
	if err != nil {
		return Result{}, err
	}
	row, err := readSnapshot(db, id)
	if err != nil {
		return Result{}, fail("Could not read the persona. Run plgkit-personas migrate.")
	}
	if row == nil {
		return Result{UserID: id, Persona: "", Matched: []string{}, Reasons: []Reason{}, CalculatedAt: ""}, nil
	}
	return *row, nil
}

func PersonaIs(userID, name string, db *sql.DB) (bool, error) {
	personaName, err := requireText(name, "persona")
	if err != nil {
		return false, err
	}
	result, err := Persona(userID, db)
	if err != nil {
		return false, err
	}
	return result.Persona == personaName, nil
}
