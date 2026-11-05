#!/usr/bin/env python3
"""Score behavior-persona predictions and audit the answer key.

The audit encodes the decision order in the rubric. It checks that every
gold label is the label that order produces. It does not call a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

LABELS = (
    "evaluator",
    "implementer",
    "champion",
    "blocked",
    "power_user",
    "unknown",
)

INQUIRY = frozenset(
    {
        "viewed_pricing",
        "viewed_docs",
        "viewed_feature_comparison",
        "viewed_security_overview",
        "viewed_case_study",
        "started_sandbox",
        "explored_sample_data",
        "asked_fit_question",
        "compared_export_formats",
        "viewed_integration_catalog",
        "bookmarked_integration",
    }
)
SUCCESS = frozenset(
    {
        "completed_setup_step",
        "connected_integration",
        "imported_production_data",
        "configured_roles",
        "mapped_fields",
        "configured_notifications",
        "created_first_workflow",
        "completed_setup",
        "switched_to_production",
    }
)
ADVOCACY = frozenset(
    {
        "invited_department",
        "sponsored_second_team",
        "shared_workspace",
        "created_internal_playbook",
        "enabled_team_template",
        "presented_to_leadership",
        "requested_procurement_packet",
        "requested_expansion_call",
        "asked_it_to_approve_rollout",
    }
)
ADVANCED = frozenset(
    {
        "used_api",
        "used_webhook",
        "created_automation",
        "ran_bulk_action",
        "used_advanced_filter",
        "saved_advanced_view",
        "scheduled_recurring_report",
        "edited_workflow",
        "resolved_queue",
        "exported_production_data",
        "customized_dashboard",
    }
)
PRODUCT_FAILURE = frozenset(
    {
        "sso_setup_failed",
        "integration_auth_failed",
        "import_failed",
        "permission_denied",
        "billing_verification_failed",
        "hit_seat_limit",
    }
)
PENDING = frozenset({"admin_approval_pending", "security_review_pending"})
ATTEMPT = frozenset({"started_setup", "started_sso_setup"})
INVITE = frozenset({"invited_teammate", "invited_reviewer"})
OBSTACLE_EXTRA = frozenset({"opened_support_ticket", "setup_abandoned"})
NOISE = frozenset(
    {
        "signed_up",
        "opened_welcome_email",
        "password_reset",
        "viewed_account_settings",
        "bounced_invoice_email",
    }
)
BATCH_INVITE = frozenset({"invited_department", "sponsored_second_team"})
ZERO_SESSION_OK = frozenset(
    {"signed_up", "opened_welcome_email", "bounced_invoice_email"}
)
KNOWN_EVENTS = (
    INQUIRY
    | SUCCESS
    | ADVOCACY
    | ADVANCED
    | PRODUCT_FAILURE
    | PENDING
    | ATTEMPT
    | INVITE
    | OBSTACLE_EXTRA
    | NOISE
)
PLANS = frozenset({"trial", "free", "team", "business", "enterprise"})
OBSTACLES = PRODUCT_FAILURE | PENDING | OBSTACLE_EXTRA

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "evals" / "behavior_personas.json"
DEFAULT_README = ROOT / "README.md"
RUBRIC_START = "<!-- rubric:start -->"
RUBRIC_END = "<!-- rubric:end -->"


def count_events(events: list[str], group: frozenset[str]) -> int:
    return sum(event in group for event in events)


def last_index(events: list[str], group: frozenset[str]) -> int:
    return max(index for index, event in enumerate(events) if event in group)


def repeated_block(events: list[str]) -> bool:
    """Same product failure twice, or a pending gate twice with a companion."""
    counts = Counter(event for event in events if event in PRODUCT_FAILURE)
    if any(n >= 2 for n in counts.values()):
        return True
    pending = count_events(events, PENDING)
    companion = any(
        event in {"opened_support_ticket", "permission_denied", "setup_abandoned"}
        for event in events
    )
    return pending >= 2 and companion


def success_after_last_obstacle(events: list[str]) -> bool:
    obstacle_at = [index for index, event in enumerate(events) if event in OBSTACLES]
    if not obstacle_at:
        return False
    last_obstacle = obstacle_at[-1]
    return any(
        event in SUCCESS and index > last_obstacle
        for index, event in enumerate(events)
    )


def real_inquiry(events: list[str]) -> bool:
    inquiry = [event for event in events if event in INQUIRY]
    kinds = set(inquiry)
    if len(kinds) >= 2 and len(inquiry) >= 3:
        return True
    sandbox = kinds & {"started_sandbox", "explored_sample_data"}
    return bool(sandbox) and len(kinds) >= 2


def is_evaluator(profile: dict) -> bool:
    if profile["setup_completed"]:
        return False
    events = profile["events"]
    if not real_inquiry(events):
        return False
    if any(event in ADVOCACY or event in ADVANCED for event in events):
        return False
    if any(event == "invited_teammate" for event in events):
        return False
    if any(event in OBSTACLE_EXTRA or event in PENDING for event in events):
        return False
    if count_events(events, PRODUCT_FAILURE) > 1:
        return False
    successes = [event for event in events if event in SUCCESS]
    if any(event != "completed_setup_step" for event in successes):
        return False
    if len(successes) > 1:
        return False
    if successes and not any(
        event in {"started_sandbox", "explored_sample_data"} for event in events
    ):
        return False
    return True


def assign_label(profile: dict) -> str:
    """Apply the rubric decision order. Stop at the first label that fits."""
    events = profile["events"]
    setup_completed = profile["setup_completed"]
    if repeated_block(events) and not success_after_last_obstacle(events):
        return "blocked"

    advocacy_n = count_events(events, ADVOCACY)
    advanced_n = count_events(events, ADVANCED)
    if advocacy_n >= 2 and advanced_n >= 2:
        if last_index(events, ADVOCACY) > last_index(events, ADVANCED):
            return "champion"
        if setup_completed:
            return "power_user"
        return "unknown"
    if advocacy_n >= 2:
        return "champion"
    if advanced_n >= 2 and setup_completed:
        return "power_user"
    if count_events(events, SUCCESS) >= 2:
        return "implementer"
    if is_evaluator(profile):
        return "evaluator"
    return "unknown"


def load_dataset(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "examples" not in data:
        raise SystemExit(f"{path} must be an object with an examples list")
    return data


def load_predictions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"{path} is empty")
    if text[0] == "[":
        data = json.loads(text)
        if not isinstance(data, list):
            raise SystemExit(f"{path} must be a JSON list or JSON lines")
        return data
    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: {exc}") from exc
        rows.append(row)
    return rows


def extract_readme_rubric(readme: str) -> str:
    try:
        start = readme.index(RUBRIC_START) + len(RUBRIC_START)
        end = readme.index(RUBRIC_END)
    except ValueError as exc:
        raise SystemExit("README is missing rubric markers") from exc
    body = readme[start:end]
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    return body


def audit(data: dict, readme: str | None = None) -> list[str]:
    """Return problems. An empty list means the key matches the rubric."""
    problems: list[str] = []

    def bad(message: str) -> None:
        problems.append(message)

    labels = data.get("labels")
    if list(labels or []) != list(LABELS):
        bad(f"labels must be {list(LABELS)}")
    if data.get("example_count") != len(data["examples"]):
        bad("example_count does not match the examples list")
    if not isinstance(data.get("rubric"), str) or not data["rubric"].strip():
        bad("rubric must be a non-empty string")
    elif readme is not None and extract_readme_rubric(readme) != data["rubric"]:
        bad("README rubric does not match the JSON rubric")

    seen_ids: set[str] = set()
    seen_roles: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    seen_events: set[tuple[str, ...]] = set()
    seen_reasons: set[str] = set()
    counts: Counter[str] = Counter()
    industries: dict[str, list[str]] = {label: [] for label in LABELS}
    plans: dict[str, set[str]] = {label: set() for label in LABELS}

    for example in data["examples"]:
        example_id = example.get("id", "<missing id>")
        expected = example.get("expected_persona")
        profile = example.get("profile")
        reason = example.get("reason")
        if not isinstance(profile, dict):
            bad(f"{example_id}: profile must be an object")
            continue
        events = profile.get("events")
        prefix = f"{example_id}: "
        if expected not in LABELS:
            bad(prefix + f"unexpected label {expected!r}")
            continue
        counts[expected] += 1
        if example_id in seen_ids:
            bad(prefix + "duplicate id")
        seen_ids.add(example_id)
        if example_id != f"{expected}_{counts[expected]:03d}":
            bad(prefix + "id does not match label order")
        if not isinstance(reason, str) or not reason.strip():
            bad(prefix + "reason must be a non-empty string")
        elif reason in seen_reasons:
            bad(prefix + "duplicate reason")
        else:
            seen_reasons.add(reason)

        for field in ("industry", "job_role", "plan"):
            if not isinstance(profile.get(field), str) or not profile[field].strip():
                bad(prefix + f"{field} must be a non-empty string")
        if profile.get("plan") not in PLANS:
            bad(prefix + f"unknown plan {profile.get('plan')!r}")
        for field in ("account_age_days", "sessions_last_7_days", "teammates_invited"):
            value = profile.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                bad(prefix + f"{field} must be a non-negative integer")
        if not isinstance(profile.get("setup_completed"), bool):
            bad(prefix + "setup_completed must be a boolean")
        if not isinstance(events, list) or any(not isinstance(event, str) for event in events):
            bad(prefix + "events must be a list of strings")
            continue
        unknown_events = sorted({event for event in events if event not in KNOWN_EVENTS})
        if unknown_events:
            bad(prefix + f"unknown events {unknown_events}")

        role = profile.get("job_role")
        industry = profile.get("industry")
        if isinstance(role, str):
            if role in seen_roles:
                bad(prefix + f"duplicate job_role {role}")
            seen_roles.add(role)
        if isinstance(role, str) and isinstance(industry, str):
            pair = (industry, role)
            if pair in seen_pairs:
                bad(prefix + "duplicate industry and job_role")
            seen_pairs.add(pair)
            industries[expected].append(industry)
        if isinstance(profile.get("plan"), str):
            plans[expected].add(profile["plan"])

        event_key = tuple(sorted(Counter(events).items()))
        if event_key in seen_events:
            bad(prefix + "duplicate event mix")
        seen_events.add(event_key)

        individual = count_events(events, INVITE)
        batch = any(event in BATCH_INVITE for event in events)
        invited = profile.get("teammates_invited")
        if isinstance(invited, int):
            if batch:
                if invited <= individual:
                    bad(prefix + "batch invite must raise teammates_invited above individual invites")
            elif invited != individual:
                bad(
                    prefix
                    + f"teammates_invited is {invited} but individual invite events total {individual}"
                )
        in_app = [event for event in events if event not in ZERO_SESSION_OK]
        sessions = profile.get("sessions_last_7_days")
        if isinstance(sessions, int) and in_app and sessions < 1:
            bad(prefix + "in-app events require at least one session")
        if profile.get("setup_completed") is False and any(
            event in {"completed_setup", "switched_to_production"} for event in events
        ):
            bad(prefix + "completed production setup contradicts setup_completed false")
        if assign_label(profile) != expected:
            bad(
                prefix
                + f"rubric assigns {assign_label(profile)}, gold says {expected}"
            )

    for label in LABELS:
        if counts[label] != 20:
            bad(f"{label} has {counts[label]} examples, expected 20")
        if len(plans[label]) < 4:
            bad(f"{label} uses only {sorted(plans[label])}")
    industry_sets = [tuple(industries[label]) for label in LABELS]
    if len(set(industry_sets)) != 1:
        bad("each label should use the same industries in the same order")
    if industry_sets and len(set(industry_sets[0])) != 20:
        bad("each label should cover 20 industries")

    blocked = next((item for item in data["examples"] if item.get("id") == "blocked_001"), None)
    issue_events = [
        "started_sso_setup",
        "sso_setup_failed",
        "started_sso_setup",
        "sso_setup_failed",
    ]
    if blocked is None:
        bad("missing blocked_001 from the issue example")
    else:
        if blocked["profile"].get("events") != issue_events:
            bad("blocked_001 events do not match the issue example")
        if blocked.get("reason") != "Repeatedly trying to complete setup but hitting the same failure.":
            bad("blocked_001 reason does not match the issue example")
        profile = blocked["profile"]
        if (
            profile.get("industry") != "healthcare"
            or profile.get("job_role") != "practice_manager"
            or profile.get("plan") != "trial"
            or profile.get("account_age_days") != 8
            or profile.get("sessions_last_7_days") != 5
            or profile.get("teammates_invited") != 0
            or profile.get("setup_completed") is not False
        ):
            bad("blocked_001 profile does not match the issue example")
    return problems


def _profile(
    events: list[str],
    *,
    setup: bool = False,
    invites: int = 0,
) -> dict:
    return {
        "industry": "test",
        "job_role": "tester",
        "plan": "trial",
        "account_age_days": 10,
        "sessions_last_7_days": 3,
        "teammates_invited": invites,
        "setup_completed": setup,
        "events": events,
    }


def self_test() -> list[str]:
    """Boundary cases the decision order has to get right."""
    cases = [
        (
            "two SSO failures",
            _profile(
                [
                    "started_sso_setup",
                    "sso_setup_failed",
                    "started_sso_setup",
                    "sso_setup_failed",
                ]
            ),
            "blocked",
        ),
        (
            "two failures then success",
            _profile(
                [
                    "integration_auth_failed",
                    "integration_auth_failed",
                    "connected_integration",
                    "mapped_fields",
                ]
            ),
            "implementer",
        ),
        (
            "two successes then a repeated failure",
            _profile(
                [
                    "mapped_fields",
                    "configured_notifications",
                    "import_failed",
                    "import_failed",
                ]
            ),
            "blocked",
        ),
        (
            "two successes then one failure",
            _profile(
                [
                    "completed_setup_step",
                    "mapped_fields",
                    "integration_auth_failed",
                ]
            ),
            "implementer",
        ),
        (
            "sandbox setup step",
            _profile(
                [
                    "started_sandbox",
                    "explored_sample_data",
                    "completed_setup_step",
                    "explored_sample_data",
                ]
            ),
            "evaluator",
        ),
        (
            "one failure inside research",
            _profile(
                [
                    "viewed_docs",
                    "viewed_feature_comparison",
                    "integration_auth_failed",
                    "explored_sample_data",
                ]
            ),
            "evaluator",
        ),
        ("repeated pricing page", _profile(["viewed_pricing"] * 4), "unknown"),
        ("two page views", _profile(["viewed_docs", "viewed_pricing"]), "unknown"),
        (
            "advanced use then advocacy",
            _profile(
                [
                    "used_api",
                    "created_automation",
                    "invited_department",
                    "requested_expansion_call",
                ],
                setup=True,
                invites=4,
            ),
            "champion",
        ),
        (
            "advocacy then advanced use",
            _profile(
                [
                    "presented_to_leadership",
                    "invited_department",
                    "used_api",
                    "used_webhook",
                    "created_automation",
                ],
                setup=True,
                invites=6,
            ),
            "power_user",
        ),
        (
            "advanced use later but setup incomplete",
            _profile(
                [
                    "presented_to_leadership",
                    "invited_department",
                    "used_api",
                    "used_webhook",
                ],
                setup=False,
                invites=6,
            ),
            "unknown",
        ),
        (
            "pending review twice",
            _profile(
                [
                    "security_review_pending",
                    "opened_support_ticket",
                    "security_review_pending",
                ]
            ),
            "blocked",
        ),
        (
            "one pending review inside advocacy",
            _profile(
                [
                    "requested_procurement_packet",
                    "presented_to_leadership",
                    "security_review_pending",
                    "shared_workspace",
                    "invited_department",
                ],
                setup=True,
                invites=9,
            ),
            "champion",
        ),
        ("signup only", _profile(["signed_up"]), "unknown"),
        (
            "working group is not advocacy",
            _profile(
                [
                    "configured_roles",
                    "invited_teammate",
                    "invited_teammate",
                    "invited_teammate",
                    "mapped_fields",
                ],
                invites=3,
            ),
            "implementer",
        ),
    ]
    problems = []
    for name, profile, expected in cases:
        got = assign_label(profile)
        if got != expected:
            problems.append(f"self-test {name}: got {got}, expected {expected}")
    return problems


def score_predictions(data: dict, rows: list[dict]) -> int:
    gold = {example["id"]: example["expected_persona"] for example in data["examples"]}
    predicted: dict[str, str] = {}
    extras: list[str] = []
    bad_rows: list[str] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            bad_rows.append(f"row {index} is not an object")
            continue
        example_id = row.get("id")
        label = row.get("predicted_persona")
        if not isinstance(example_id, str) or not isinstance(label, str):
            bad_rows.append(f"row {index} needs string id and predicted_persona")
            continue
        if label not in LABELS:
            bad_rows.append(f"{example_id}: predicted_persona {label!r} is not a label")
            continue
        if example_id not in gold:
            extras.append(example_id)
            continue
        if example_id in predicted:
            bad_rows.append(f"{example_id}: duplicate prediction")
            continue
        predicted[example_id] = label
    if bad_rows:
        for line in bad_rows:
            print(line, file=sys.stderr)
        return 1

    missing = [example_id for example_id in gold if example_id not in predicted]
    correct = sum(1 for example_id, label in gold.items() if predicted.get(example_id) == label)
    total = len(gold)
    print(f"accuracy {correct}/{total} ({correct / total:.1%})")

    print()
    print(f"{'label':<14} {'gold':>5} {'pred':>5} {'hit':>5} {'recall':>8} {'precision':>10}")
    for label in LABELS:
        gold_ids = [example_id for example_id, gold_label in gold.items() if gold_label == label]
        pred_ids = [example_id for example_id, pred_label in predicted.items() if pred_label == label]
        hits = sum(1 for example_id in gold_ids if predicted.get(example_id) == label)
        recall = "n/a" if not gold_ids else f"{hits / len(gold_ids):.1%}"
        precision = "n/a" if not pred_ids else f"{hits / len(pred_ids):.1%}"
        print(
            f"{label:<14} {len(gold_ids):>5} {len(pred_ids):>5} {hits:>5} {recall:>8} {precision:>10}"
        )

    print()
    print("confusion (rows are gold, columns are predicted)")
    header = " ".join(f"{label[:6]:>6}" for label in LABELS) + f" {'miss':>6}"
    print(f"{'':<14} {header}")
    for gold_label in LABELS:
        cells = []
        for pred_label in LABELS:
            n = sum(
                1
                for example_id, expected in gold.items()
                if expected == gold_label and predicted.get(example_id) == pred_label
            )
            cells.append(f"{n:>6}")
        missed = sum(
            1
            for example_id, expected in gold.items()
            if expected == gold_label and example_id not in predicted
        )
        print(f"{gold_label:<14} {' '.join(cells)} {missed:>6}")

    mismatches = [
        (example_id, gold[example_id], predicted[example_id])
        for example_id in gold
        if example_id in predicted and predicted[example_id] != gold[example_id]
    ]
    if mismatches or missing or extras:
        print()
    for example_id, expected, got in mismatches:
        print(f"mismatch {example_id}: gold {expected}, predicted {got}")
    if missing:
        print(f"missing {len(missing)}: {', '.join(missing)}")
    if extras:
        print(f"ignored unknown ids: {', '.join(extras)}")
    return 0


def run_check(data_path: Path, readme_path: Path) -> int:
    data = load_dataset(data_path)
    readme = readme_path.read_text(encoding="utf-8")
    problems = self_test() + audit(data, readme)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"{len(problems)} problem(s)", file=sys.stderr)
        return 1
    counts = Counter(example["expected_persona"] for example in data["examples"])
    summary = ", ".join(f"{label} {counts[label]}" for label in LABELS)
    print(f"ok {len(data['examples'])} examples ({summary})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="gold JSON and predictions file (JSON list or JSON lines)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="audit the answer key and the boundary cases",
    )
    args = parser.parse_args(argv)
    if args.check:
        if args.paths:
            data_path = Path(args.paths[0])
        else:
            data_path = DEFAULT_DATA
        return run_check(data_path, DEFAULT_README)
    if len(args.paths) != 2:
        parser.error("give the gold JSON and a predictions file, or pass --check")
    data = load_dataset(Path(args.paths[0]))
    rows = load_predictions(Path(args.paths[1]))
    return score_predictions(data, rows)


if __name__ == "__main__":
    sys.exit(main())
