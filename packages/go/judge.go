package plgkit

import (
	"sort"
	"strconv"
	"strings"
	"time"
)

const reasonLimit = 5

type Reason struct {
	Kind       string `json:"kind"`
	Action     string `json:"action,omitempty"`
	OccurredAt string `json:"occurred_at,omitempty"`
	Key        string `json:"key,omitempty"`
	Equals     string `json:"equals,omitempty"`
}

type Result struct {
	UserID       string   `json:"user_id"`
	Persona      string   `json:"persona"`
	Matched      []string `json:"matched"`
	Reasons      []Reason `json:"reasons"`
	CalculatedAt string   `json:"calculated_at"`
}

type preparedEvent struct {
	action     string
	occurredAt time.Time
	seq        int
}

func Judge(userID string, events []map[string]any, traits map[string]string, rules Rules, now string) (Result, error) {
	id, err := requireText(userID, "user_id")
	if err != nil {
		return Result{}, err
	}
	var moment time.Time
	if now == "" {
		moment = time.Now().UTC()
	} else {
		moment, err = ParseTime(now)
		if err != nil {
			return Result{}, err
		}
	}
	stored := map[string]string{}
	for key, value := range traits {
		stored[strings.TrimSpace(key)] = value
	}
	prepared, err := prepareEvents(events)
	if err != nil {
		return Result{}, err
	}
	ordered := append([]PersonaRule{}, rules.Personas...)
	sort.Slice(ordered, func(i, j int) bool {
		if ordered[i].Priority != ordered[j].Priority {
			return ordered[i].Priority < ordered[j].Priority
		}
		return ordered[i].Order < ordered[j].Order
	})
	matched := []string{}
	var winner *PersonaRule
	for i := range ordered {
		if matches(&ordered[i], prepared, stored, moment) {
			matched = append(matched, ordered[i].Name)
			if winner == nil {
				winner = &ordered[i]
			}
		}
	}
	reasons := []Reason{}
	personaName := ""
	if winner != nil {
		personaName = winner.Name
		reasons = reasonsFor(winner, prepared, stored, moment)
	}
	return Result{
		UserID:       id,
		Persona:      personaName,
		Matched:      matched,
		Reasons:      reasons,
		CalculatedAt: FormatTime(moment),
	}, nil
}

func ParseTime(value any) (time.Time, error) {
	text, ok := value.(string)
	if !ok {
		return time.Time{}, fail("occurred_at must be an ISO-8601 timestamp with a timezone.")
	}
	text = strings.TrimSpace(text)
	if strings.HasSuffix(text, "Z") {
		text = text[:len(text)-1] + "+00:00"
	}
	if !hasZone(text) {
		return time.Time{}, fail("occurred_at must include a timezone, for example 2026-11-09T15:00:00Z.")
	}
	parsed, err := time.Parse(time.RFC3339Nano, text)
	if err != nil {
		return time.Time{}, fail("occurred_at must be an ISO-8601 timestamp with a timezone.")
	}
	return parsed.UTC(), nil
}

func FormatTime(moment time.Time) string {
	return moment.UTC().Format("2006-01-02T15:04:05.000000Z")
}

func requireText(value, name string) (string, error) {
	if strings.TrimSpace(value) == "" {
		return "", fail(name + " is required.")
	}
	return strings.TrimSpace(value), nil
}

func hasZone(text string) bool {
	if len(text) < 6 {
		return false
	}
	tail := text[len(text)-6:]
	return (tail[0] == '+' || tail[0] == '-') && tail[3] == ':'
}

func matches(persona *PersonaRule, events []preparedEvent, traits map[string]string, moment time.Time) bool {
	for i := range persona.RequireAll {
		if !holds(&persona.RequireAll[i], events, traits, moment) {
			return false
		}
	}
	if len(persona.RequireOneOf) > 0 {
		anyTrue := false
		for i := range persona.RequireOneOf {
			if holds(&persona.RequireOneOf[i], events, traits, moment) {
				anyTrue = true
				break
			}
		}
		if !anyTrue {
			return false
		}
	}
	for i := range persona.Exclude {
		if holds(&persona.Exclude[i], events, traits, moment) {
			return false
		}
	}
	return true
}

func holds(condition *Condition, events []preparedEvent, traits map[string]string, moment time.Time) bool {
	if condition.Kind == "trait" {
		return traits[condition.Key] == condition.Equals
	}
	count := len(counted(condition, events, moment))
	if count < condition.AtLeast {
		return false
	}
	if condition.AtMost != nil && count > *condition.AtMost {
		return false
	}
	return true
}

func counted(condition *Condition, events []preparedEvent, moment time.Time) []preparedEvent {
	start := moment.Add(-time.Duration(condition.WithinDays) * 24 * time.Hour)
	actions := map[string]bool{}
	for _, action := range condition.Actions {
		actions[action] = true
	}
	found := []preparedEvent{}
	for _, event := range events {
		if !actions[event.action] {
			continue
		}
		if event.occurredAt.Before(start) || event.occurredAt.After(moment) {
			continue
		}
		found = append(found, event)
	}
	return found
}

func reasonsFor(persona *PersonaRule, events []preparedEvent, traits map[string]string, moment time.Time) []Reason {
	supporting := []Condition{}
	for _, condition := range append(append([]Condition{}, persona.RequireAll...), persona.RequireOneOf...) {
		copy := condition
		if holds(&copy, events, traits, moment) {
			supporting = append(supporting, condition)
		}
	}
	seen := map[string]bool{}
	chosen := []preparedEvent{}
	for i := range supporting {
		if supporting[i].Kind != "count" {
			continue
		}
		for _, event := range counted(&supporting[i], events, moment) {
			key := FormatTime(event.occurredAt) + "\x00" + event.action + "\x00" + strconv.Itoa(event.seq)
			if seen[key] {
				continue
			}
			seen[key] = true
			chosen = append(chosen, event)
		}
	}
	sort.Slice(chosen, func(i, j int) bool {
		return lessPrepared(chosen[j], chosen[i])
	})
	reasons := []Reason{}
	for _, event := range chosen {
		reasons = append(reasons, Reason{Kind: "event", Action: event.action, OccurredAt: FormatTime(event.occurredAt)})
	}
	for _, condition := range supporting {
		if condition.Kind == "trait" {
			reasons = append(reasons, Reason{Kind: "trait", Key: condition.Key, Equals: condition.Equals})
		}
	}
	if len(reasons) > reasonLimit {
		reasons = reasons[:reasonLimit]
	}
	return reasons
}

func prepareEvents(events []map[string]any) ([]preparedEvent, error) {
	if events == nil {
		events = []map[string]any{}
	}
	prepared := []preparedEvent{}
	for index, event := range events {
		if event == nil {
			return nil, fail("each event must be an object.")
		}
		action, ok := event["action"].(string)
		if !ok || strings.TrimSpace(action) == "" {
			return nil, fail("each event needs an action.")
		}
		occurredAt, err := ParseTime(event["occurred_at"])
		if err != nil {
			return nil, err
		}
		prepared = append(prepared, preparedEvent{action: strings.TrimSpace(action), occurredAt: occurredAt, seq: index})
	}
	return prepared, nil
}

func lessPrepared(a, b preparedEvent) bool {
	if !a.occurredAt.Equal(b.occurredAt) {
		return a.occurredAt.Before(b.occurredAt)
	}
	if a.action != b.action {
		return a.action < b.action
	}
	return a.seq < b.seq
}
