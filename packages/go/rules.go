package plgkit

import (
	"os"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

type Rules struct {
	Groups   map[string][]string
	Personas []PersonaRule
}

type PersonaRule struct {
	Name         string
	Priority     int
	Order        int
	RequireAll   []Condition
	RequireOneOf []Condition
	Exclude      []Condition
}

type Condition struct {
	Kind       string
	Actions    []string
	AtLeast    int
	AtMost     *int
	WithinDays int
	Key        string
	Equals     string
}

func LoadRules(path string) (Rules, error) {
	if path == "" {
		path = defaultRulesPath()
	}
	if path == "" {
		return NormalizeRules(map[string]any{"groups": map[string]any{}, "personas": []any{}})
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return Rules{}, fail("Could not read personas.yml.")
	}
	var parsed any
	if err := yaml.Unmarshal(raw, &parsed); err != nil {
		return Rules{}, fail("Could not read personas.yml.")
	}
	return NormalizeRules(parsed)
}

func defaultRulesPath() string {
	candidate := "plgkit/personas/personas.yml"
	info, err := os.Stat(candidate)
	if err == nil && !info.IsDir() {
		return candidate
	}
	return ""
}

func NormalizeRules(raw any) (Rules, error) {
	if rules, ok := raw.(Rules); ok {
		return rules, nil
	}
	root, ok := asMap(raw)
	if !ok {
		if raw == nil {
			root = map[string]any{}
		} else {
			return Rules{}, fail("personas.yml must be a mapping.")
		}
	}
	for key := range root {
		if key != "groups" && key != "personas" {
			return Rules{}, fail("Unknown rules key: " + key + ".")
		}
	}
	groups, err := readGroups(root["groups"])
	if err != nil {
		return Rules{}, err
	}
	items, _ := asList(root["personas"])
	if root["personas"] != nil && items == nil {
		return Rules{}, fail("personas must be a list.")
	}
	names := map[string]bool{}
	personas := []PersonaRule{}
	for index, item := range items {
		persona, err := readPersona(item, groups)
		if err != nil {
			return Rules{}, err
		}
		if names[persona.Name] {
			return Rules{}, fail("Duplicate persona: " + persona.Name + ".")
		}
		names[persona.Name] = true
		persona.Order = index
		personas = append(personas, persona)
	}
	if groups == nil {
		groups = map[string][]string{}
	}
	return Rules{Groups: groups, Personas: personas}, nil
}

func readGroups(raw any) (map[string][]string, error) {
	if raw == nil {
		return map[string][]string{}, nil
	}
	source, ok := asMap(raw)
	if !ok {
		return nil, fail("groups must be a mapping of name to actions.")
	}
	groups := map[string][]string{}
	for name, actions := range source {
		if strings.TrimSpace(name) == "" {
			return nil, fail("group names must be non-empty strings.")
		}
		list, ok := asList(actions)
		if !ok || len(list) == 0 {
			return nil, fail(name + " needs a list of actions.")
		}
		cleaned := []string{}
		for _, action := range list {
			text, ok := action.(string)
			if !ok || strings.TrimSpace(text) == "" {
				return nil, fail(name + " actions must be non-empty strings.")
			}
			cleaned = append(cleaned, strings.TrimSpace(text))
		}
		groups[strings.TrimSpace(name)] = cleaned
	}
	return groups, nil
}

func readPersona(raw any, groups map[string][]string) (PersonaRule, error) {
	item, ok := asMap(raw)
	if !ok {
		return PersonaRule{}, fail("each persona must be a mapping.")
	}
	for key := range item {
		switch key {
		case "name", "priority", "require_all", "require_one_of", "exclude":
		default:
			return PersonaRule{}, fail("Unknown persona key: " + key + ".")
		}
	}
	name, _ := item["name"].(string)
	if strings.TrimSpace(name) == "" {
		return PersonaRule{}, fail("persona name is required.")
	}
	name = strings.TrimSpace(name)
	if _, ok := item["priority"]; !ok {
		return PersonaRule{}, fail(name + " needs a priority.")
	}
	priority, err := wholeNumber("priority", item["priority"], nil)
	if err != nil {
		return PersonaRule{}, err
	}
	requireAll, err := conditions(item["require_all"], "require_all", groups, name)
	if err != nil {
		return PersonaRule{}, err
	}
	requireOne, err := conditions(item["require_one_of"], "require_one_of", groups, name)
	if err != nil {
		return PersonaRule{}, err
	}
	exclude, err := conditions(item["exclude"], "exclude", groups, name)
	if err != nil {
		return PersonaRule{}, err
	}
	return PersonaRule{
		Name:         name,
		Priority:     priority,
		RequireAll:   requireAll,
		RequireOneOf: requireOne,
		Exclude:      exclude,
	}, nil
}

func conditions(raw any, field string, groups map[string][]string, personaName string) ([]Condition, error) {
	if raw == nil {
		return []Condition{}, nil
	}
	list, ok := asList(raw)
	if !ok {
		return nil, fail(personaName + " " + field + " must be a list.")
	}
	found := []Condition{}
	for _, item := range list {
		condition, err := oneCondition(item, groups, personaName)
		if err != nil {
			return nil, err
		}
		found = append(found, condition)
	}
	return found, nil
}

func oneCondition(raw any, groups map[string][]string, personaName string) (Condition, error) {
	item, ok := asMap(raw)
	if !ok || len(item) != 1 {
		return Condition{}, fail(personaName + " conditions must be a count or a trait.")
	}
	var kind string
	var body any
	for key, value := range item {
		kind = key
		body = value
	}
	if kind == "count" {
		return readCount(body, groups, personaName)
	}
	if kind == "trait" {
		return readTrait(body, personaName)
	}
	return Condition{}, fail(personaName + " conditions must be a count or a trait.")
}

func readCount(raw any, groups map[string][]string, personaName string) (Condition, error) {
	body, ok := asMap(raw)
	if !ok {
		return Condition{}, fail(personaName + " count must be a mapping.")
	}
	for key := range body {
		switch key {
		case "action", "actions", "group", "at_least", "at_most", "within_days":
		default:
			return Condition{}, fail("Unknown count key: " + key + ".")
		}
	}
	choices := []string{}
	for _, key := range []string{"action", "actions", "group"} {
		if value, ok := body[key]; ok && value != nil {
			choices = append(choices, key)
		}
	}
	if len(choices) != 1 {
		return Condition{}, fail(personaName + " count needs one of action, actions, or group.")
	}
	var actions []string
	switch choices[0] {
	case "action":
		action, _ := body["action"].(string)
		if strings.TrimSpace(action) == "" {
			return Condition{}, fail(personaName + " action must be a non-empty string.")
		}
		actions = []string{strings.TrimSpace(action)}
	case "actions":
		list, ok := asList(body["actions"])
		if !ok || len(list) == 0 {
			return Condition{}, fail(personaName + " actions must be a list.")
		}
		for _, action := range list {
			text, _ := action.(string)
			if strings.TrimSpace(text) == "" {
				return Condition{}, fail(personaName + " actions must be non-empty strings.")
			}
			actions = append(actions, strings.TrimSpace(text))
		}
	default:
		group, _ := body["group"].(string)
		group = strings.TrimSpace(group)
		if group == "" {
			return Condition{}, fail(personaName + " group must be a non-empty string.")
		}
		found, ok := groups[group]
		if !ok {
			return Condition{}, fail("Unknown group: " + group + ".")
		}
		actions = append([]string{}, found...)
	}
	if _, ok := body["at_least"]; !ok {
		return Condition{}, fail(personaName + " count needs at_least.")
	}
	atLeast, err := wholeNumber("at_least", body["at_least"], intPtr(0))
	if err != nil {
		return Condition{}, err
	}
	var atMost *int
	if value, ok := body["at_most"]; ok && value != nil {
		parsed, err := wholeNumber("at_most", value, intPtr(0))
		if err != nil {
			return Condition{}, err
		}
		if parsed < atLeast {
			return Condition{}, fail("at_most must be at least at_least.")
		}
		atMost = &parsed
	}
	if _, ok := body["within_days"]; !ok {
		return Condition{}, fail(personaName + " count needs within_days.")
	}
	within, err := wholeNumber("within_days", body["within_days"], intPtr(1))
	if err != nil {
		return Condition{}, err
	}
	return Condition{Kind: "count", Actions: actions, AtLeast: atLeast, AtMost: atMost, WithinDays: within}, nil
}

func readTrait(raw any, personaName string) (Condition, error) {
	body, ok := asMap(raw)
	if !ok {
		return Condition{}, fail(personaName + " trait must be a mapping.")
	}
	for key := range body {
		if key != "key" && key != "equals" {
			return Condition{}, fail("Unknown trait key: " + key + ".")
		}
	}
	key, _ := body["key"].(string)
	if strings.TrimSpace(key) == "" {
		return Condition{}, fail(personaName + " trait key is required.")
	}
	equals, ok := body["equals"].(string)
	if !ok {
		return Condition{}, fail(personaName + " trait equals must be a string.")
	}
	return Condition{Kind: "trait", Key: strings.TrimSpace(key), Equals: equals}, nil
}

func wholeNumber(name string, value any, minimum *int) (int, error) {
	number, ok := asInt(value)
	if !ok {
		return 0, fail(name + " must be a whole number.")
	}
	if minimum != nil && number < *minimum {
		if *minimum == 1 {
			return 0, fail(name + " must be a whole number of 1 or more.")
		}
		return 0, fail(name + " must be a whole number of 0 or more.")
	}
	return number, nil
}

func asInt(value any) (int, bool) {
	switch typed := value.(type) {
	case int:
		return typed, true
	case int64:
		return int(typed), true
	case float64:
		if typed != float64(int(typed)) {
			return 0, false
		}
		return int(typed), true
	case string:
		if typed == "" {
			return 0, false
		}
		number, err := strconv.Atoi(typed)
		if err != nil {
			return 0, false
		}
		return number, true
	default:
		return 0, false
	}
}

func asMap(value any) (map[string]any, bool) {
	switch typed := value.(type) {
	case map[string]any:
		return typed, true
	case map[string]string:
		out := map[string]any{}
		for key, item := range typed {
			out[key] = item
		}
		return out, true
	default:
		return nil, false
	}
}

func asList(value any) ([]any, bool) {
	switch typed := value.(type) {
	case []any:
		return typed, true
	case nil:
		return nil, false
	default:
		return nil, false
	}
}

func intPtr(value int) *int { return &value }
