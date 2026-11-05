# Personas

Scored answer key for behavior personas on product activity. Use it to compare a model's label with the expected label. Do not train on this file, and do not put these examples in the prompt. Few-shot rows taken from the key inflate the score.

The label is the behavior in the recent window, not a permanent type of person. The same person can be an evaluator, then an implementer, then blocked or a champion. When a window contains more than one stretch of behavior, the rubric's decision order says which label wins.

## File

[`evals/behavior_personas.json`](evals/behavior_personas.json)

120 examples: 20 each for `evaluator`, `implementer`, `champion`, `blocked`, `power_user`, and `unknown`.

`unknown` is not one of the five behavior personas. It is the label when the window does not establish one. Each value the model is allowed to return has the same number of examples.

Each example has the shape from the issue:

```json
{
  "id": "blocked_001",
  "expected_persona": "blocked",
  "profile": {
    "industry": "healthcare",
    "job_role": "practice_manager",
    "plan": "trial",
    "account_age_days": 8,
    "sessions_last_7_days": 5,
    "teammates_invited": 0,
    "setup_completed": false,
    "events": [
      "started_sso_setup",
      "sso_setup_failed",
      "started_sso_setup",
      "sso_setup_failed"
    ]
  },
  "reason": "Repeatedly trying to complete setup but hitting the same failure."
}
```

`profile.events` is chronological, oldest first. It is the recent activity that matters, not a lifetime log. `reason` is the review note for that row. Withhold `expected_persona` and `reason` from the model.

Industries are balanced across labels so the industry is not the answer. Plans are mixed for the same reason. The rubric says those fields are context.

## Score a model

1. Pass the model the `rubric` string in the JSON file, verbatim, then one `profile` object.
2. The rubric tells the model to return one label and no other text.
3. Save one object per example, as a JSON list or as JSON lines:

```json
{"id": "blocked_001", "predicted_persona": "blocked"}
```

4. Compare the file with the key:

```bash
python3 evals/score.py evals/behavior_personas.json predictions.jsonl
```

The script prints overall accuracy, recall and precision by label, a confusion matrix, and each mismatch. It does not call a model. A missing id counts against accuracy.

Check that the key still matches the rubric, and that the rubric in this README matches the JSON file:

```bash
python3 evals/score.py --check
```

## Rubric

The text between the markers is the `rubric` field. Give that text to the model unchanged.

<!-- rubric:start -->
Label the behavior in the recent window. Do not treat the label as a permanent type of person. The same person can move from one label to another.

`events` is chronological, oldest first. It is the recent activity that matters, not a full history. The other profile fields are the current state. Industry, job role, plan, account age, and session count are context. They do not assign the label by themselves.

Return exactly one of: evaluator, implementer, champion, blocked, power_user, unknown.
Return the label only, with no other text.

Event groups:

- Inquiry: viewed_pricing, viewed_docs, viewed_feature_comparison, viewed_security_overview, viewed_case_study, started_sandbox, explored_sample_data, asked_fit_question, compared_export_formats, viewed_integration_catalog, bookmarked_integration.
- Successful setup: completed_setup_step, connected_integration, imported_production_data, configured_roles, mapped_fields, configured_notifications, created_first_workflow, completed_setup, switched_to_production.
- Advocacy: invited_department, sponsored_second_team, shared_workspace, created_internal_playbook, enabled_team_template, presented_to_leadership, requested_procurement_packet, requested_expansion_call, asked_it_to_approve_rollout.
- Advanced use: used_api, used_webhook, created_automation, ran_bulk_action, used_advanced_filter, saved_advanced_view, scheduled_recurring_report, edited_workflow, resolved_queue, exported_production_data, customized_dashboard.
- Product failure: sso_setup_failed, integration_auth_failed, import_failed, permission_denied, billing_verification_failed, hit_seat_limit.
- Pending gate: admin_approval_pending, security_review_pending.

Other events:

- started_setup and started_sso_setup are attempts. They are not successful setup.
- invited_teammate is a working-group invite. invited_reviewer is a fit-check invite. Neither is advocacy by itself.
- opened_support_ticket and setup_abandoned record an obstacle. They are not successes.
- signed_up, opened_welcome_email, password_reset, viewed_account_settings, and bounced_invoice_email are noise.

A real inquiry is two different inquiry events totaling at least three events, or a sandbox or sample-data event plus a different inquiry event. Repeating one inquiry event is still one kind of inquiry.

A repeated block is the same product failure at least twice, or a pending gate at least twice together with a support ticket, a permission denial, or an abandoned setup.

Decision order. Stop at the first label that fits.

1. blocked. A repeated block is present, and no successful setup event comes after the last product failure, pending gate, support ticket, or abandonment.
2. Advocacy and advanced use both occur at least twice. Compare the last event of each group. If the last advocacy event is later, the label is champion. If the last advanced-use event is later and setup is complete, the label is power_user. If the last advanced-use event is later and setup is not complete, the label is unknown.
3. champion. Advocacy events occur at least twice. A single pending gate does not stop this step. A repeated block was already handled by step 1.
4. power_user. Setup is complete, and advanced-use events occur at least twice.
5. implementer. Successful setup events occur at least twice.
6. evaluator. Setup is not complete, and the window is a real inquiry. Invites, if any, are invited_reviewer only. There is no advocacy, no advanced use, no support ticket, no abandoned setup, and no pending gate. At most one product failure appears. The only successful setup event allowed is a single completed_setup_step, and only when a sandbox or sample-data event is also present.
7. unknown. None of the labels above fit. This includes noise, an empty window, a glance that is not a real inquiry, and a setup that was opened and dropped with no successful step and no repeated block.

One event does not establish champion or power_user. One product failure does not establish blocked, even when it is the last event. One or two inquiry events, or the same inquiry event repeated, do not establish evaluator. The same product failure twice establishes blocked when no successful setup event comes after it, even if successful setup events came earlier. A repeated failure followed by a successful setup event is not blocked.
<!-- rubric:end -->

## Not in this repo

No model weights, no training loop, and no live customer data.
