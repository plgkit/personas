package plgkit

import (
	"sort"
	"strings"
	"time"
)

const reasonLimit = 5

var supports = map[string]map[string]bool{
	"champion":    {"invite_sent": true},
	"power_user":  {"core_action": true},
	"blocked":     {"core_action": true, "invite_sent": true, "setup_step": true},
	"implementer": {"setup_step": true},
	"evaluator":   {"core_action": true, "invite_sent": true, "setup_step": true},
	"unknown":     {},
}

type Reason struct {
	Action     string `json:"action"`
	Category   string `json:"category"`
	OccurredAt string `json:"occurred_at"`
}

type Result struct {
	UserID       string         `json:"user_id"`
	Persona      string         `json:"persona"`
	Reasons      []Reason       `json:"reasons"`
	Counts       map[string]int `json:"counts"`
	Matched      []string       `json:"matched"`
	CalculatedAt string         `json:"calculated_at"`
}

type countedEvent struct {
	action     string
	category   string
	occurredAt time.Time
	seq        int
}

func Judge(userID string, events []map[string]any, mapping map[string]string, policy map[string]any, now string) (Result, error) {
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
	rules, err := NormalizePolicy(policy)
	if err != nil {
		return Result{}, err
	}
	categories, err := NormalizeMapping(mapping)
	if err != nil {
		return Result{}, err
	}
	counted, err := inWindow(events, categories, moment, rules["lookback_days"])
	if err != nil {
		return Result{}, err
	}
	counts := map[string]int{"core_action": 0, "invite_sent": 0, "setup_step": 0}
	for _, event := range counted {
		counts[event.category]++
	}
	var newest time.Time
	hasNewest := len(counted) > 0
	if hasNewest {
		newest = counted[len(counted)-1].occurredAt
	}
	silenceAt := moment.Add(-time.Duration(rules["silence_days"]) * 24 * time.Hour)
	quiet := hasNewest && !newest.After(silenceAt)
	started := counts["setup_step"] >= 1 || counts["core_action"] >= 1
	matched := []string{}
	if counts["invite_sent"] >= rules["champion_min"] {
		matched = append(matched, "champion")
	}
	if counts["core_action"] >= rules["power_user_min"] {
		matched = append(matched, "power_user")
	}
	if started && quiet {
		matched = append(matched, "blocked")
	}
	if counts["setup_step"] >= rules["implementer_min"] {
		matched = append(matched, "implementer")
	}
	if len(counted) > 0 {
		matched = append(matched, "evaluator")
	}
	personaName := "unknown"
	if len(matched) > 0 {
		personaName = matched[0]
	}
	return Result{
		UserID:       id,
		Persona:      personaName,
		Reasons:      reasonList(counted, personaName),
		Counts:       counts,
		Matched:      matched,
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
	if len(tail) == 6 && (tail[0] == '+' || tail[0] == '-') && tail[3] == ':' {
		return true
	}
	return false
}

func inWindow(events []map[string]any, mapping map[string]string, moment time.Time, lookbackDays int) ([]countedEvent, error) {
	if events == nil {
		events = []map[string]any{}
	}
	start := moment.Add(-time.Duration(lookbackDays) * 24 * time.Hour)
	allowed := categorySet()
	var counted []countedEvent
	for index, event := range events {
		if event == nil {
			return nil, fail("each event must be an object.")
		}
		action, ok := event["action"].(string)
		if !ok || strings.TrimSpace(action) == "" {
			return nil, fail("each event needs an action.")
		}
		action = strings.TrimSpace(action)
		category := mapping[action]
		if !allowed[category] {
			continue
		}
		occurredAt, err := ParseTime(event["occurred_at"])
		if err != nil {
			return nil, err
		}
		if occurredAt.Before(start) || occurredAt.After(moment) {
			continue
		}
		counted = append(counted, countedEvent{action: action, category: category, occurredAt: occurredAt, seq: index})
	}
	sort.Slice(counted, func(i, j int) bool {
		return lessEvent(counted[i], counted[j])
	})
	return counted, nil
}

func reasonList(counted []countedEvent, personaName string) []Reason {
	allowed := supports[personaName]
	var supported []countedEvent
	for _, event := range counted {
		if allowed[event.category] {
			supported = append(supported, event)
		}
	}
	sort.Slice(supported, func(i, j int) bool {
		return lessEvent(supported[j], supported[i])
	})
	if len(supported) > reasonLimit {
		supported = supported[:reasonLimit]
	}
	reasons := []Reason{}
	for _, event := range supported {
		reasons = append(reasons, Reason{
			Action:     event.action,
			Category:   event.category,
			OccurredAt: FormatTime(event.occurredAt),
		})
	}
	return reasons
}

func lessEvent(a, b countedEvent) bool {
	if !a.occurredAt.Equal(b.occurredAt) {
		return a.occurredAt.Before(b.occurredAt)
	}
	if a.action != b.action {
		return a.action < b.action
	}
	return a.seq < b.seq
}
