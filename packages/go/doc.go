// Package plgkit saves product events and judges one persona per user.
// The database address lives in an environment variable named by
// database_url_env in config.yml. A postgres:// or postgresql:// address uses
// Postgres. If that variable is unset, plgkit uses a SQLite file,
// plgkit_events.sqlite, in the current directory.
package plgkit
